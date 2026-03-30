"""Pipeline enrichment API routes."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.db import get_db
from src.dependencies.auth import get_current_user, require_admin_user, require_admin_or_internal_key
from src.models.pipeline_job import PipelineJob
from src.models.user import User
from src.pipeline.repositories.job_repository import JobRepository
from src.pipeline.schemas.enrichment_schemas import (
    CacheStatusResponse,
    EnrichRequest,
    EnrichResponse,
    EnrichmentStatus,
    CachedValue,
    JobInfo,
    JobStatusResponse,
    ShortlistEnrichRequest,
)
from src.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# --- Public endpoints ---


@router.post("/enrich", response_model=EnrichResponse)
async def trigger_enrichment(
    request: EnrichRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger enrichment for a single entity.

    Returns cached data if fresh, otherwise enqueues an enrichment job.
    """
    service = EnrichmentService(db)
    result = service.enrich_entity(
        entity_kind=request.entity_kind.value,
        entity_id=request.entity_id,
        user_id=str(current_user.id),
        priority=request.priority.value,
        force_refresh=request.force_refresh,
    )

    response = EnrichResponse(
        status=EnrichmentStatus(result.status),
        message=result.message,
    )

    if result.cache_entry:
        response.cache = CachedValue(
            value=result.cache_entry.value_json,
            confidence=float(result.cache_entry.confidence) if result.cache_entry.confidence else None,
            computed_at=result.cache_entry.computed_at,
            expires_at=result.cache_entry.expires_at,
        )

    if result.job:
        response.job = JobInfo(
            job_id=str(result.job.id),
            status=result.job.status,
            priority=result.job.priority,
        )

    return response


@router.post("/enrich/shortlist", response_model=list[EnrichResponse])
async def trigger_shortlist_enrichment(
    request: ShortlistEnrichRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch enrichment for up to 20 entities (e.g., a user's shortlist)."""
    service = EnrichmentService(db)
    responses = []

    for item in request.items:
        result = service.enrich_entity(
            entity_kind=item.entity_kind.value,
            entity_id=item.entity_id,
            user_id=str(current_user.id),
            priority=item.priority.value,
            force_refresh=item.force_refresh,
        )

        resp = EnrichResponse(
            status=EnrichmentStatus(result.status),
            message=result.message,
        )
        if result.cache_entry:
            resp.cache = CachedValue(
                value=result.cache_entry.value_json,
                confidence=float(result.cache_entry.confidence) if result.cache_entry.confidence else None,
                computed_at=result.cache_entry.computed_at,
                expires_at=result.cache_entry.expires_at,
            )
        if result.job:
            resp.job = JobInfo(
                job_id=str(result.job.id),
                status=result.job.status,
                priority=result.job.priority,
            )
        responses.append(resp)

    return responses


@router.get("/cache/status", response_model=CacheStatusResponse)
async def get_cache_status(
    entity_kind: str = Query(...),
    entity_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check cache freshness for an entity."""
    service = EnrichmentService(db)
    info = service.get_cache_status(entity_kind, entity_id)
    return CacheStatusResponse(**info)


@router.get("/cache/value")
async def get_cache_value(
    entity_kind: str = Query(...),
    entity_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the cached enrichment value for an entity."""
    service = EnrichmentService(db)
    value = service.get_cache_value(entity_kind, entity_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cached enrichment found",
        )
    return value


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll the status of an enrichment job."""
    repo = JobRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress=job.output_json.get("progress") if job.output_json else None,
        confidence=job.output_json.get("confidence") if job.output_json else None,
        error=job.error_message,
        queued_at=job.queued_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


# --- Admin endpoints ---


@router.post("/admin/refresh")
async def admin_force_refresh(
    request: EnrichRequest,
    _auth: str = Depends(require_admin_or_internal_key),
    db: Session = Depends(get_db),
):
    """Force refresh an entity (admin only, bypasses quota)."""
    service = EnrichmentService(db)
    result = service.enrich_entity(
        entity_kind=request.entity_kind.value,
        entity_id=request.entity_id,
        user_id=None,  # No quota check for admin
        priority=request.priority.value,
        force_refresh=True,
    )

    resp = {"status": result.status, "message": result.message}
    if result.job:
        resp["job_id"] = str(result.job.id)
    return resp


@router.post("/admin/jobs/{job_id}/rerun")
async def admin_rerun_job(
    job_id: str,
    _auth: str = Depends(require_admin_or_internal_key),
    db: Session = Depends(get_db),
):
    """Retry a failed job (admin only)."""
    repo = JobRepository(db)
    job = repo.requeue_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not found, not failed, or max attempts reached",
        )
    db.commit()
    return {"job_id": str(job.id), "status": job.status}


@router.post("/admin/jobs/{job_id}/cancel")
async def admin_cancel_job(
    job_id: str,
    _auth: str = Depends(require_admin_or_internal_key),
    db: Session = Depends(get_db),
):
    """Cancel a queued job (admin only)."""
    repo = JobRepository(db)
    cancelled = repo.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not found or not in queued state",
        )
    db.commit()
    return {"job_id": job_id, "status": "canceled"}


@router.get("/admin/domains")
async def admin_domain_health(
    _auth: str = Depends(require_admin_or_internal_key),
    db: Session = Depends(get_db),
):
    """Domain health overview (admin only)."""
    from src.pipeline.services.domain_health_service import DomainHealthService

    service = DomainHealthService()
    return service.get_all_health(db)


@router.post("/admin/cache/purge")
async def admin_purge_cache(
    max_age_days: int = Query(90),
    _auth: str = Depends(require_admin_or_internal_key),
    db: Session = Depends(get_db),
):
    """Purge expired cache entries (admin only)."""
    from datetime import datetime, timedelta

    from src.models.enrichment_cache import EnrichmentCache

    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    count = (
        db.query(EnrichmentCache)
        .filter(EnrichmentCache.expires_at < cutoff)
        .delete(synchronize_session="fetch")
    )
    db.commit()
    return {"purged": count}
