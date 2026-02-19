"""Maintenance Celery tasks for pipeline housekeeping."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="pipeline.maintenance.purge_expired_cache")
def purge_expired_cache() -> dict:
    """Delete expired enrichment_cache rows.

    Runs daily to keep the cache table lean.
    """
    from src.db import SessionLocal
    from src.models.enrichment_cache import EnrichmentCache

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        count = (
            db.query(EnrichmentCache)
            .filter(EnrichmentCache.expires_at <= now)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Purged %d expired enrichment cache entries", count)
        return {"purged": count}
    except Exception as exc:
        db.rollback()
        logger.error("purge_expired_cache failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


@shared_task(name="pipeline.maintenance.reset_domain_health")
def reset_domain_health() -> dict:
    """Reset blocked domains that have been in cooldown long enough.

    Runs weekly so domains get a second chance.
    """
    from src.pipeline.services.domain_health_service import DomainHealthService

    service = DomainHealthService()
    count = service.reset_stale_blocks(older_than_days=7)
    return {"domains_reset": count}


@shared_task(name="pipeline.maintenance.cleanup_old_jobs")
def cleanup_old_jobs(days: int = 90) -> dict:
    """Archive (delete) pipeline_jobs older than N days.

    Keeps the jobs table from growing indefinitely. Only removes
    completed/failed/canceled jobs; running jobs are never touched.
    """
    from src.db import SessionLocal
    from src.models.pipeline_job import PipelineJob

    cutoff = datetime.utcnow() - timedelta(days=days)
    terminal_statuses = ("succeeded", "failed", "canceled", "skipped")

    db = SessionLocal()
    try:
        count = (
            db.query(PipelineJob)
            .filter(
                PipelineJob.created_at <= cutoff,
                PipelineJob.status.in_(terminal_statuses),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Cleaned up %d old pipeline jobs (older than %d days)", count, days)
        return {"deleted": count, "cutoff_days": days}
    except Exception as exc:
        db.rollback()
        logger.error("cleanup_old_jobs failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()
