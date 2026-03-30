"""Celery tasks for dossier and professor match pipelines."""
from __future__ import annotations

import logging

import httpx

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="pipeline.run_dossier",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError, httpx.TimeoutException, httpx.ConnectError),
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_dossier_pipeline(self, job_id: str) -> dict:
    """Run the dossier pipeline for a given job.

    Same pattern as run_enrichment_pipeline:
    claim job → acquire inflight slot → acquire dedup lock → invoke graph
    → complete job → release lock → release inflight slot.
    """
    from src.config import settings
    from src.db import SessionLocal
    from src.pipeline.redis_keyspace import acquire_lock, release_lock
    from src.pipeline.redis_keyspace.inflight import acquire_inflight, release_inflight
    from src.pipeline.repositories.job_repository import JobRepository

    db = SessionLocal()
    inflight_acquired = False
    fingerprint: str | None = None
    try:
        repo = JobRepository(db)

        # 1. Claim the job
        job = repo.claim_job(job_id, run_by=f"celery:{self.request.hostname or 'worker'}")
        db.commit()
        if job is None:
            logger.info("Dossier job %s already claimed or not queued, skipping", job_id)
            return {"status": "skipped", "reason": "already_claimed"}

        fingerprint = job.fingerprint

        # 2. Worker-side inflight cap enforcement
        inflight = acquire_inflight("dossier", max_concurrent=settings.max_concurrent_dossier_jobs)
        if not inflight.acquired:
            # Re-queue with a short backoff; the job stays "queued" for the next pickup
            repo.complete_job(job_id, status="queued", error_message=None)
            db.commit()
            logger.info(
                "Inflight cap reached (%d/%d), re-queuing dossier job %s",
                inflight.current, inflight.maximum, job_id,
            )
            raise self.retry(exc=None, countdown=30)
        inflight_acquired = True

        # 3. Acquire dedup lock
        lock_acquired = acquire_lock(fingerprint, str(job.id), ttl_ms=600_000)
        if not lock_acquired:
            repo.complete_job(job_id, status="skipped", error_message="Dedup lock held")
            db.commit()
            return {"status": "skipped", "reason": "dedup_locked"}

        try:
            # 4. Run dossier graph
            from src.pipeline.orchestrator.dossier_graph import create_dossier_graph

            graph = create_dossier_graph()
            input_json = job.input_json or {}

            initial_state = {
                "job_id": str(job.id),
                "pipeline_job_id": str(job.id),
                "job_type": input_json.get("dossier_type", "school_dossier"),
                "entity_kind": job.entity_kind or "school",
                "entity_id": str(job.entity_id) if job.entity_id else None,
                "user_id": input_json.get("user_id"),
                "program_name": input_json.get("program_name"),
                "degree_level": input_json.get("degree_level"),
                "recommendation_session_id": input_json.get("recommendation_session_id"),
                "progress": [],
            }

            run_config = {"configurable": {"thread_id": str(job.id)}}
            result = graph.invoke(initial_state, config=run_config)

            # 5. Complete the job
            status = result.get("status", "succeeded")
            repo.complete_job(
                job_id,
                status="succeeded" if status != "failed" else "failed",
                output_json={
                    "progress": result.get("progress", []),
                    "confidence": result.get("confidence"),
                    "promoted": result.get("promote", False),
                    "fallback_used": result.get("fallback_used", False),
                },
                error_message=result.get("error"),
            )
            db.commit()

            return {
                "status": status,
                "confidence": result.get("confidence"),
                "progress": result.get("progress", []),
            }

        finally:
            release_lock(fingerprint, str(job.id))

    except Exception as exc:
        db.rollback()
        logger.error("Dossier pipeline failed for job %s: %s", job_id, exc, exc_info=True)

        try:
            repo = JobRepository(db)
            repo.complete_job(job_id, status="failed", error_message=str(exc))
            db.commit()
        except Exception:
            db.rollback()

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        if inflight_acquired:
            release_inflight("dossier")
        db.close()


@celery_app.task(
    name="pipeline.run_professor_match",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError, httpx.TimeoutException, httpx.ConnectError),
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_professor_match_pipeline(self, job_id: str) -> dict:
    """Run the professor match pipeline for a given job."""
    from src.config import settings
    from src.db import SessionLocal
    from src.pipeline.redis_keyspace import acquire_lock, release_lock
    from src.pipeline.redis_keyspace.inflight import acquire_inflight, release_inflight
    from src.pipeline.repositories.job_repository import JobRepository

    db = SessionLocal()
    inflight_acquired = False
    fingerprint: str | None = None
    try:
        repo = JobRepository(db)

        job = repo.claim_job(job_id, run_by=f"celery:{self.request.hostname or 'worker'}")
        db.commit()
        if job is None:
            return {"status": "skipped", "reason": "already_claimed"}

        fingerprint = job.fingerprint

        # Worker-side inflight cap enforcement
        inflight = acquire_inflight("professor_match", max_concurrent=settings.max_concurrent_dossier_jobs)
        if not inflight.acquired:
            repo.complete_job(job_id, status="queued", error_message=None)
            db.commit()
            logger.info(
                "Inflight cap reached (%d/%d), re-queuing professor match job %s",
                inflight.current, inflight.maximum, job_id,
            )
            raise self.retry(exc=None, countdown=30)
        inflight_acquired = True

        lock_acquired = acquire_lock(fingerprint, str(job.id), ttl_ms=600_000)
        if not lock_acquired:
            repo.complete_job(job_id, status="skipped", error_message="Dedup lock held")
            db.commit()
            return {"status": "skipped", "reason": "dedup_locked"}

        try:
            from src.pipeline.orchestrator.professor_graph import create_professor_match_graph

            graph = create_professor_match_graph()
            input_json = job.input_json or {}

            initial_state = {
                "job_id": str(job.id),
                "pipeline_job_id": str(job.id),
                "entity_kind": "school",
                "entity_id": str(job.entity_id) if job.entity_id else None,
                "user_id": input_json.get("user_id"),
                "user_interests": input_json.get("research_interests", []),
                "department": input_json.get("department"),
                "progress": [],
            }

            run_config = {"configurable": {"thread_id": str(job.id)}}
            result = graph.invoke(initial_state, config=run_config)

            status = result.get("status", "succeeded")
            repo.complete_job(
                job_id,
                status="succeeded" if status != "failed" else "failed",
                output_json={
                    "progress": result.get("progress", []),
                    "confidence": result.get("confidence"),
                    "professors_found": len(result.get("ranked_professors", [])),
                },
                error_message=result.get("error"),
            )
            db.commit()

            return {
                "status": status,
                "confidence": result.get("confidence"),
                "professors_found": len(result.get("ranked_professors", [])),
            }

        finally:
            release_lock(fingerprint, str(job.id))

    except Exception as exc:
        db.rollback()
        logger.error("Professor match pipeline failed for job %s: %s", job_id, exc, exc_info=True)

        try:
            repo = JobRepository(db)
            repo.complete_job(job_id, status="failed", error_message=str(exc))
            db.commit()
        except Exception:
            db.rollback()

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        if inflight_acquired:
            release_inflight("professor_match")
        db.close()
