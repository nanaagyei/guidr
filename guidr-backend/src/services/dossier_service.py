"""Dossier service: cache check, quota, dedup, job dispatch for dossier/professor/recommendation jobs."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.models.enrichment_cache import EnrichmentCache
from src.models.pipeline_job import PipelineJob
from src.pipeline.redis_keyspace.quota import check_and_increment_quota
from src.pipeline.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

# Freshness buckets for dossier types
DOSSIER_FRESHNESS = {
    "recommendation_run": ("recommendation_run:7d", 7),
    "school_dossier": ("school_dossier:30d", 30),
    "professor_match": ("professor_matches:30d", 30),
    "funding_dossier": ("funding_dossier:14d", 14),
}


class DossierResult:
    """Return type for dossier service methods."""

    def __init__(
        self,
        status: str,
        cache_entry: Optional[EnrichmentCache] = None,
        job: Optional[PipelineJob] = None,
        message: Optional[str] = None,
    ):
        self.status = status
        self.cache_entry = cache_entry
        self.job = job
        self.message = message


class DossierService:
    """Orchestrates dossier requests: cache → quota → dedup → dispatch."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def request_school_dossier(
        self,
        school_id: str,
        user_id: Optional[str] = None,
        force: bool = False,
    ) -> DossierResult:
        """Request a school dossier."""
        return self._request(
            dossier_type="school_dossier",
            entity_kind="school",
            entity_id=school_id,
            user_id=user_id,
            force=force,
        )

    def request_funding_dossier(
        self,
        school_id: str,
        user_id: Optional[str] = None,
        program_id: Optional[str] = None,
        force: bool = False,
    ) -> DossierResult:
        """Request a funding dossier."""
        return self._request(
            dossier_type="funding_dossier",
            entity_kind="school",
            entity_id=school_id,
            user_id=user_id,
            force=force,
            extra_input={"program_id": program_id} if program_id else {},
        )

    def request_professor_matches(
        self,
        school_id: str,
        user_id: Optional[str] = None,
        research_interests: Optional[list[str]] = None,
        department: Optional[str] = None,
        force: bool = False,
    ) -> DossierResult:
        """Request professor matching."""
        return self._request(
            dossier_type="professor_match",
            entity_kind="school",
            entity_id=school_id,
            user_id=user_id,
            force=force,
            extra_input={
                "research_interests": research_interests or [],
                "department": department,
            },
        )

    def request_recommendations(
        self,
        user_id: str,
        trigger_source: Optional[str] = None,
        session_id: Optional[str] = None,
        force: bool = False,
    ) -> DossierResult:
        """Request AI-powered recommendations."""
        extra = {"trigger_source": trigger_source or "manual"}
        if session_id:
            extra["recommendation_session_id"] = session_id
        return self._request(
            dossier_type="recommendation_run",
            entity_kind="user",
            entity_id=user_id,
            user_id=user_id,
            force=force,
            extra_input=extra,
        )

    def _request(
        self,
        dossier_type: str,
        entity_kind: str,
        entity_id: str,
        user_id: Optional[str] = None,
        force: bool = False,
        extra_input: Optional[dict] = None,
    ) -> DossierResult:
        """Generic dossier request flow."""
        freshness_bucket, days = DOSSIER_FRESHNESS.get(dossier_type, ("30d", 30))

        # 1. Cache check (per-user first, then global fallback)
        if not force:
            cache_entry = self._get_valid_cache(entity_kind, entity_id, freshness_bucket, user_id)
            if cache_entry:
                cache_entry.hit_count += 1
                cache_entry.last_hit_at = datetime.utcnow()
                self.db.flush()
                return DossierResult(status="cache_hit", cache_entry=cache_entry)

        # 2. Quota check
        if user_id:
            quota = check_and_increment_quota(user_id, resource="dossier", period="day")
            if not quota.allowed:
                return DossierResult(
                    status="quota_exceeded",
                    message=f"Daily dossier limit reached ({quota.limit}). Resets tomorrow.",
                )

        # 3. Dedup check
        job_type = self._job_type_for(dossier_type)
        existing = self.repo.find_in_progress(
            job_type=job_type,
            entity_kind=entity_kind,
            entity_id=entity_id,
            freshness_bucket=freshness_bucket,
        )
        if existing:
            return DossierResult(
                status="dedup_in_progress",
                job=existing,
                message="Request already in progress.",
            )

        # 3.5 Global inflight cap — prevent resource exhaustion
        from src.config import settings as _settings
        from src.pipeline.redis_keyspace.inflight import acquire_inflight

        inflight_service = "professor_match" if dossier_type == "professor_match" else "dossier"
        inflight = acquire_inflight(inflight_service, max_concurrent=_settings.max_concurrent_dossier_jobs)
        if not inflight.acquired:
            # Still create the job record so the client can poll status later
            input_json_cap: dict = {
                "dossier_type": dossier_type,
                "user_id": user_id,
                "force_refresh": force,
                "cap_queued": True,
            }
            if extra_input:
                input_json_cap.update(extra_input)
            try:
                cap_job = self.repo.create_job(
                    job_type=job_type,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    priority="low",
                    freshness_bucket=freshness_bucket,
                    input_json=input_json_cap,
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            return DossierResult(
                status="queued_cap_exceeded",
                job=cap_job,
                message=(
                    f"Server at capacity ({inflight.current}/{inflight.maximum} jobs running). "
                    "Your request is queued. Poll job_id for status."
                ),
            )

        # 4. Create pipeline job (or recycle existing one for force reruns)
        input_json = {
            "dossier_type": dossier_type,
            "user_id": user_id,
            "force_refresh": force,
        }
        if extra_input:
            input_json.update(extra_input)

        try:
            job = self.repo.create_job(
                job_type=job_type,
                entity_kind=entity_kind,
                entity_id=entity_id,
                priority="high",
                freshness_bucket=freshness_bucket,
                input_json=input_json,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            if force:
                # Fingerprint collision with a completed/failed job — recycle it
                job = self.repo.find_by_fingerprint(
                    job_type=job_type,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    freshness_bucket=freshness_bucket,
                )
                if job:
                    job.status = "queued"
                    job.error_message = None
                    job.error_code = None
                    job.started_at = None
                    job.finished_at = None
                    job.run_by = None
                    job.attempt = 0
                    job.input_json = input_json
                    self.db.commit()
                    logger.info("Recycled existing job %s for force rerun", job.id)
                else:
                    raise
            else:
                raise

        # 5. Dispatch to Celery
        self._dispatch(job, dossier_type)

        return DossierResult(status="enqueued", job=job)

    def _get_valid_cache(
        self,
        entity_kind: str,
        entity_id: str,
        freshness_bucket: str,
        user_id: Optional[str] = None,
    ) -> Optional[EnrichmentCache]:
        """Get a valid (non-expired) cache entry.

        Lookup strategy:
        1. Prefer a per-user entry (user_id matches) if user_id is provided.
        2. Fall back to a global entry (user_id IS NULL) if no per-user entry found.
        """
        try:
            entity_uuid = uuid.UUID(entity_id)
            now = datetime.utcnow()
            base_filter = [
                EnrichmentCache.entity_kind == entity_kind,
                EnrichmentCache.entity_id == entity_uuid,
                EnrichmentCache.freshness_bucket == freshness_bucket,
                EnrichmentCache.expires_at > now,
            ]

            if user_id:
                # Try per-user entry first
                user_uuid = uuid.UUID(user_id)
                entry = (
                    self.db.query(EnrichmentCache)
                    .filter(*base_filter, EnrichmentCache.user_id == user_uuid)
                    .first()
                )
                if entry:
                    return entry

            # Fall back to global entry
            entry = (
                self.db.query(EnrichmentCache)
                .filter(*base_filter, EnrichmentCache.user_id.is_(None))
                .first()
            )
            return entry
        except Exception:
            # Rollback so the session isn't stuck in a failed transaction state
            self.db.rollback()
        return None

    def _job_type_for(self, dossier_type: str) -> str:
        """Map dossier type to pipeline job type."""
        return {
            "school_dossier": "dossier",
            "funding_dossier": "dossier",
            "professor_match": "professor_match",
            "recommendation_run": "dossier",
        }.get(dossier_type, "dossier")

    def _dispatch(self, job: PipelineJob, dossier_type: str) -> None:
        """Dispatch job to appropriate Celery task.

        In development mode (no Celery worker), runs the pipeline synchronously.
        In production, dispatches to Celery with inline fallback on failure.
        """
        from src.config import settings

        if settings.pipeline_env == "development":
            logger.info("Dev mode: running %s pipeline inline for job %s", dossier_type, job.id)
            self._run_inline(job, dossier_type)
            return

        try:
            if dossier_type == "professor_match":
                from src.pipeline.tasks.dossier_tasks import run_professor_match_pipeline
                run_professor_match_pipeline.delay(str(job.id))
            else:
                from src.pipeline.tasks.dossier_tasks import run_dossier_pipeline
                run_dossier_pipeline.delay(str(job.id))
            logger.info("Dispatched %s pipeline for job %s", dossier_type, job.id)
        except Exception as exc:
            logger.warning(
                "Celery dispatch failed for %s job %s (%s), running inline",
                dossier_type, job.id, exc,
            )
            self._run_inline(job, dossier_type)

    def _run_inline(self, job: PipelineJob, dossier_type: str) -> None:
        """Run the pipeline synchronously (fallback when Celery is unavailable).

        Mirrors the Celery task logic but runs in the request thread.
        """
        from src.db import SessionLocal

        db = SessionLocal()
        try:
            repo = JobRepository(db)

            # Claim the job
            claimed = repo.claim_job(str(job.id), run_by="inline")
            db.commit()
            if claimed is None:
                logger.info("Inline: job %s already claimed, skipping", job.id)
                return

            input_json = job.input_json or {}

            if dossier_type == "professor_match":
                from src.pipeline.orchestrator.professor_graph import create_professor_match_graph
                graph = create_professor_match_graph()
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
            else:
                from src.pipeline.orchestrator.dossier_graph import create_dossier_graph
                graph = create_dossier_graph()
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

            status = result.get("status", "succeeded")
            repo.complete_job(
                str(job.id),
                status="succeeded" if status != "failed" else "failed",
                output_json={
                    "progress": result.get("progress", []),
                    "confidence": result.get("confidence"),
                },
                error_message=result.get("error"),
            )
            db.commit()
            logger.info("Inline %s pipeline completed for job %s", dossier_type, job.id)

        except Exception as exc:
            db.rollback()
            logger.error("Inline %s pipeline failed for job %s: %s", dossier_type, job.id, exc)
            try:
                repo = JobRepository(db)
                repo.complete_job(str(job.id), status="failed", error_message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()
