"""Celery tasks for the LangGraph orchestrator pipeline."""
from __future__ import annotations

import logging

import httpx

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="pipeline.run_enrichment",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError, httpx.TimeoutException, httpx.ConnectError),
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_enrichment_pipeline(self, job_id: str) -> dict:
    """Run the LangGraph enrichment pipeline for a given job.

    1. Claim the job (atomic status update)
    2. Acquire dedup lock
    3. Run the orchestrator graph
    4. Release lock
    5. Complete the job with outcome
    """
    from src.db import SessionLocal
    from src.pipeline.repositories.job_repository import JobRepository
    from src.pipeline.redis_keyspace import acquire_lock, release_lock
    from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint

    db = SessionLocal()
    try:
        repo = JobRepository(db)

        # 1. Claim the job
        job = repo.claim_job(job_id, run_by=f"celery:{self.request.hostname or 'worker'}")
        db.commit()
        if job is None:
            logger.info("Job %s already claimed or not queued, skipping", job_id)
            return {"status": "skipped", "reason": "already_claimed"}

        fingerprint = job.fingerprint

        # 2. Acquire dedup lock
        lock_acquired = acquire_lock(fingerprint, str(job.id), ttl_ms=600_000)
        if not lock_acquired:
            repo.complete_job(job_id, status="skipped", error_message="Dedup lock held by another worker")
            db.commit()
            return {"status": "skipped", "reason": "dedup_locked"}

        try:
            # 3. Run orchestrator graph
            from src.pipeline.orchestrator import create_orchestrator_graph

            graph = create_orchestrator_graph()
            initial_state = {
                "job_id": str(job.id),
                "pipeline_job_id": str(job.id),
                "entity_kind": job.entity_kind or "school",
                "entity_id": str(job.entity_id) if job.entity_id else None,
                "category": job.input_json.get("category", "SCHOOL_OVERVIEW") if job.input_json else "SCHOOL_OVERVIEW",
                "priority": job.priority or "high",
                "schema_version": job.schema_version or "v1",
                "retry_count": job.attempt - 1,
                "max_attempts": job.max_attempts,
                "progress": [],
            }

            run_config = {"configurable": {"thread_id": str(job.id)}}
            result = graph.invoke(initial_state, config=run_config)

            # 4. Complete the job
            status = result.get("status", "succeeded")
            if status in ("failed", "retrying"):
                repo.complete_job(
                    job_id,
                    status="failed",
                    output_json={
                        "progress": result.get("progress", []),
                        "confidence": result.get("confidence"),
                    },
                    error_message=result.get("error"),
                )
            else:
                repo.complete_job(
                    job_id,
                    status="succeeded",
                    output_json={
                        "progress": result.get("progress", []),
                        "confidence": result.get("confidence"),
                        "promoted": result.get("promote", False),
                    },
                )
            db.commit()

            return {
                "status": status,
                "confidence": result.get("confidence"),
                "progress": result.get("progress", []),
            }

        finally:
            # 5. Release dedup lock
            release_lock(fingerprint, str(job.id))

    except Exception as exc:
        db.rollback()
        logger.error("Enrichment pipeline failed for job %s: %s", job_id, exc, exc_info=True)

        # Mark failed in DB
        try:
            repo = JobRepository(db)
            repo.complete_job(job_id, status="failed", error_message=str(exc))
            db.commit()
        except Exception:
            db.rollback()

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
