"""Enrichment service: cache check, quota, dedup, job dispatch."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.models.enrichment_cache import EnrichmentCache
from src.models.pipeline_job import PipelineJob
from src.pipeline.redis_keyspace import acquire_lock, release_lock
from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
from src.pipeline.redis_keyspace.quota import check_and_increment_quota
from src.pipeline.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

# Staleness windows per entity kind (days)
STALENESS_WINDOWS = {
    "school": 30,
    "program": 14,
    "professor": 30,
    "funding": 14,
}

# Category mapping for staleness
FRESHNESS_BUCKETS = {
    "school": "30d",
    "program": "14d",
    "professor": "30d",
    "funding": "14d",
}


class EnrichmentResult:
    """Return type for enrich_entity."""

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


class EnrichmentService:
    """Orchestrates enrichment requests: cache -> quota -> dedup -> dispatch."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = JobRepository(db)

    def enrich_entity(
        self,
        entity_kind: str,
        entity_id: str,
        user_id: Optional[str] = None,
        priority: str = "high",
        force_refresh: bool = False,
    ) -> EnrichmentResult:
        """Main enrichment flow.

        1. Check enrichment_cache for unexpired entry -> cache_hit
        2. Check user quota -> quota_exceeded
        3. Check dedup (in-progress job) -> dedup_in_progress
        4. Create pipeline_job
        5. Dispatch to Celery
        6. Return job info
        """
        freshness_bucket = FRESHNESS_BUCKETS.get(entity_kind, "30d")

        # 1. Cache check (skip if force_refresh)
        if not force_refresh:
            cache_entry = self._get_valid_cache(entity_kind, entity_id, freshness_bucket)
            if cache_entry:
                # Bump hit count
                cache_entry.hit_count += 1
                cache_entry.last_hit_at = datetime.utcnow()
                self.db.flush()
                return EnrichmentResult(status="cache_hit", cache_entry=cache_entry)

        # 2. Quota check
        if user_id:
            quota = check_and_increment_quota(user_id, resource="enrich", period="day")
            if not quota.allowed:
                return EnrichmentResult(
                    status="quota_exceeded",
                    message=f"Daily enrichment limit reached ({quota.limit}). Resets tomorrow.",
                )

        # 3. Dedup check -- is there already a queued/running job?
        existing = self.repo.find_in_progress(
            job_type="enrichment",
            entity_kind=entity_kind,
            entity_id=entity_id,
        )
        if existing:
            return EnrichmentResult(
                status="dedup_in_progress",
                job=existing,
                message="Enrichment already in progress.",
            )

        # 4. Create pipeline job
        try:
            job = self.repo.create_job(
                job_type="enrichment",
                entity_kind=entity_kind,
                entity_id=entity_id,
                priority=priority,
                freshness_bucket=freshness_bucket,
                input_json={"force_refresh": force_refresh},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        # 5. Dispatch to Celery
        self._dispatch(job)

        return EnrichmentResult(status="enqueued", job=job)

    def get_cache_status(
        self,
        entity_kind: str,
        entity_id: str,
    ) -> dict:
        """Return cache freshness info for an entity."""
        freshness_bucket = FRESHNESS_BUCKETS.get(entity_kind, "30d")
        cache = self._get_cache_entry(entity_kind, entity_id, freshness_bucket)
        now = datetime.utcnow()

        if cache:
            is_stale = cache.expires_at < now if cache.expires_at else True
            return {
                "has_cache": True,
                "confidence": float(cache.confidence) if cache.confidence else None,
                "computed_at": cache.computed_at,
                "expires_at": cache.expires_at,
                "is_stale": is_stale,
            }

        return {"has_cache": False, "is_stale": True}

    def get_cache_value(
        self,
        entity_kind: str,
        entity_id: str,
    ) -> Optional[dict]:
        """Return cached enrichment value if available."""
        freshness_bucket = FRESHNESS_BUCKETS.get(entity_kind, "30d")
        cache = self._get_cache_entry(entity_kind, entity_id, freshness_bucket)
        if cache:
            cache.hit_count += 1
            cache.last_hit_at = datetime.utcnow()
            self.db.flush()
            return cache.value_json
        return None

    def _get_valid_cache(
        self, entity_kind: str, entity_id: str, freshness_bucket: str
    ) -> Optional[EnrichmentCache]:
        """Get cache entry only if not expired."""
        entry = self._get_cache_entry(entity_kind, entity_id, freshness_bucket)
        if entry and entry.expires_at and entry.expires_at > datetime.utcnow():
            return entry
        return None

    def _get_cache_entry(
        self, entity_kind: str, entity_id: str, freshness_bucket: str
    ) -> Optional[EnrichmentCache]:
        """Get cache entry regardless of expiry."""
        return (
            self.db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.entity_kind == entity_kind,
                EnrichmentCache.entity_id == uuid.UUID(entity_id),
                EnrichmentCache.freshness_bucket == freshness_bucket,
            )
            .first()
        )

    def _dispatch(self, job: PipelineJob) -> None:
        """Dispatch job to Celery. Uses orchestrator task if available,
        falls back to legacy scrape tasks."""
        try:
            from src.pipeline.tasks.orchestrator_tasks import run_enrichment_pipeline

            run_enrichment_pipeline.delay(str(job.id))
            logger.info("Dispatched orchestrator pipeline for job %s", job.id)
        except (ImportError, Exception) as exc:
            # Fallback to legacy pipeline task
            logger.info(
                "Orchestrator unavailable (%s), falling back to legacy pipeline for job %s",
                exc,
                job.id,
            )
            try:
                from src.pipeline.tasks.pipeline_tasks import run_full_pipeline

                entity_id = str(job.entity_id) if job.entity_id else None
                if entity_id and job.entity_kind == "school":
                    run_full_pipeline.delay(entity_id)
            except Exception as fallback_exc:
                logger.error("Failed to dispatch job %s: %s", job.id, fallback_exc)
