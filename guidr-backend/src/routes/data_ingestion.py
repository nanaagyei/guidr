"""Admin-only ingestion and pipeline endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import get_db
from src.dependencies.auth import require_admin_or_internal_key
from src.services.data_ingestion import DataIngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


# ------------------------------------------------------------------
# Existing ingestion endpoints
# ------------------------------------------------------------------

class IPEDSIngestionRequest(BaseModel):
    year: str = "2022"
    limit: int | None = None


@router.post("/schools/ipeds")
async def trigger_ipeds_ingestion(
    payload: IPEDSIngestionRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    service = DataIngestionService(db)
    return service.ingest_ipeds(year=payload.year, limit=payload.limit)


@router.post("/schools/scorecard")
async def trigger_scorecard_enrichment(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    service = DataIngestionService(db)
    return service.enrich_with_scorecard()


class ScorecardLoadRequest(BaseModel):
    state: Optional[str] = None
    limit: Optional[int] = None
    async_run: bool = False


@router.post("/schools/scorecard/load")
async def trigger_scorecard_load(
    payload: ScorecardLoadRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    """Load graduate schools from College Scorecard API (bulk).

    Use async_run=True to queue as Celery task for large loads.
    """
    if payload.async_run:
        from src.workers.scraper_worker import load_graduate_schools_from_scorecard_task
        async_result = load_graduate_schools_from_scorecard_task.delay(
            state=payload.state,
            limit=payload.limit,
        )
        return {
            "message": "Scorecard load queued",
            "async": True,
            "task_id": str(async_result.id),
            "task": "ingestion.load_scorecard_schools",
        }
    service = DataIngestionService(db)
    return service.load_graduate_schools_from_scorecard(
        state=payload.state,
        limit=payload.limit,
    )


@router.post("/search/reindex")
async def trigger_search_reindex(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    service = DataIngestionService(db)
    return service.reindex_search()


# ------------------------------------------------------------------
# Pipeline endpoints
# ------------------------------------------------------------------

class PipelineTriggerRequest(BaseModel):
    institution_id: str


class BatchPipelineRequest(BaseModel):
    institution_ids: List[str]


@router.post("/pipeline/run")
async def trigger_pipeline_for_institution(
    payload: PipelineTriggerRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    """Trigger the full scraping pipeline for a single institution."""
    from src.models.institution import Institution

    institution = db.query(Institution).filter(
        Institution.id == UUID(payload.institution_id)
    ).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    from src.pipeline.tasks.pipeline_tasks import run_full_pipeline
    run_full_pipeline.delay(payload.institution_id)

    return {
        "message": f"Pipeline queued for {institution.name}",
        "institution_id": payload.institution_id,
    }


@router.post("/pipeline/batch")
async def trigger_batch_pipeline(
    payload: BatchPipelineRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    """Trigger the pipeline for multiple institutions."""
    from src.pipeline.tasks.pipeline_tasks import batch_scrape_institutions
    batch_scrape_institutions.delay(payload.institution_ids)

    return {
        "message": f"Batch pipeline queued for {len(payload.institution_ids)} institutions",
    }


@router.get("/pipeline/jobs")
async def list_scrape_jobs(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
    institution_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List scrape jobs with optional filtering."""
    from src.models.scrape_job import ScrapeJob

    query = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc())

    if institution_id:
        query = query.filter(ScrapeJob.institution_id == UUID(institution_id))
    if status:
        query = query.filter(ScrapeJob.status == status)

    total = query.count()
    jobs = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "jobs": [
            {
                "id": str(j.id),
                "institution_id": str(j.institution_id) if j.institution_id else None,
                "job_type": j.job_type,
                "status": j.status,
                "pages_scraped": j.pages_scraped,
                "items_extracted": j.items_extracted,
                "error_message": j.error_message,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ],
    }


@router.get("/pipeline/jobs/{job_id}")
async def get_scrape_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    """Get details of a specific scrape job."""
    from src.models.scrape_job import ScrapeJob

    job = db.query(ScrapeJob).filter(ScrapeJob.id == UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scrape job not found")

    return {
        "id": str(job.id),
        "institution_id": str(job.institution_id) if job.institution_id else None,
        "job_type": job.job_type,
        "status": job.status,
        "pages_scraped": job.pages_scraped,
        "items_extracted": job.items_extracted,
        "quality_score": job.quality_score,
        "error_message": job.error_message,
        "raw_data_path": job.raw_data_path,
        "metadata": job.metadata_,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }


# ------------------------------------------------------------------
# Bulk enrichment endpoint (LangGraph orchestrator)
# ------------------------------------------------------------------

_VALID_CATEGORIES = {
    "school": "SCHOOL_OVERVIEW",
    "program": "PROGRAM_REQUIREMENTS",
    "professor": "FACULTY_DIRECTORY",
    "funding": "PROGRAM_FUNDING",
}


class BulkEnrichRequest(BaseModel):
    """Request body for bulk LangGraph enrichment."""
    entity_kind: str = "school"
    category: Optional[str] = None          # Defaults per entity_kind (see _VALID_CATEGORIES)
    limit: Optional[int] = None             # None = all entities
    skip_if_enriched_within_hours: int = 168  # 7 days
    priority: str = "bulk"


@router.post("/pipeline/bulk-enrich")
async def bulk_enrich(
    payload: BulkEnrichRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_or_internal_key),
):
    """Queue LangGraph enrichment jobs for all entities of the given kind.

    - Checks the enrichment_cache: skips entities enriched within
      `skip_if_enriched_within_hours`.
    - Deduplicates via the JobRepository fingerprint mechanism so running
      this twice does not double-queue.
    - Returns counts of queued vs. skipped entities.

    Typical usage after a fresh College Scorecard load:
        POST /ingestion/pipeline/bulk-enrich {"entity_kind": "school"}
        POST /ingestion/pipeline/bulk-enrich {"entity_kind": "program"}
    """
    from datetime import datetime, timedelta
    from src.models.institution import Institution
    from src.models.program import Program
    from src.models.professor import Professor
    from src.models.funding_opportunity import FundingOpportunity
    from src.models.enrichment_cache import EnrichmentCache
    from src.services.enrichment_service import EnrichmentService, FRESHNESS_BUCKETS
    from src.pipeline.tasks.orchestrator_tasks import run_enrichment_pipeline
    from src.pipeline.repositories.job_repository import JobRepository

    entity_kind = payload.entity_kind.lower()
    if entity_kind not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"entity_kind must be one of: {list(_VALID_CATEGORIES.keys())}",
        )

    category = payload.category or _VALID_CATEGORIES[entity_kind]
    cutoff = datetime.utcnow() - timedelta(hours=payload.skip_if_enriched_within_hours)
    freshness_bucket = FRESHNESS_BUCKETS.get(entity_kind, "30d")
    # Must match JobRepository.create_job defaults so fingerprint dedup is consistent.
    job_freshness_bucket = "default"

    # Fetch entity IDs + website hints
    if entity_kind == "school":
        rows = db.query(Institution.id, Institution.website_url, Institution.name).all()
    elif entity_kind == "program":
        rows = db.query(Program.id, Program.website_url, Program.name).all()
    elif entity_kind == "professor":
        rows = db.query(Professor.id, Professor.personal_page_url, Professor.full_name).all()
    else:
        rows = db.query(FundingOpportunity.id, FundingOpportunity.website_url, FundingOpportunity.name).all()

    if payload.limit:
        rows = rows[: payload.limit]

    # Find recently enriched entity IDs (skip those)
    recently_enriched_ids: set[str] = set()
    if rows:
        all_ids = [str(r[0]) for r in rows]
        cached = (
            db.query(EnrichmentCache.entity_id)
            .filter(
                EnrichmentCache.entity_kind == entity_kind,
                EnrichmentCache.freshness_bucket == freshness_bucket,
                EnrichmentCache.computed_at >= cutoff,
            )
            .all()
        )
        recently_enriched_ids = {str(c[0]) for c in cached}

    repo = JobRepository(db)
    queued = 0
    skipped = 0

    for entity_id, website_url, entity_name in rows:
        entity_id_str = str(entity_id)

        if entity_id_str in recently_enriched_ids:
            skipped += 1
            continue

        target_url = str(website_url).strip() if website_url else None

        # Dedup via JobRepository fingerprint (same inputs as create_job).
        if repo.find_in_progress(
            job_type="run_enrichment_pipeline",
            entity_kind=entity_kind,
            entity_id=entity_id_str,
            target_url=target_url,
            schema_version="v1",
            freshness_bucket=job_freshness_bucket,
        ):
            skipped += 1
            continue

        if repo.find_recent_success(
            job_type="run_enrichment_pipeline",
            entity_kind=entity_kind,
            entity_id=entity_id_str,
            target_url=target_url,
            schema_version="v1",
            freshness_bucket=job_freshness_bucket,
            window_hours=payload.skip_if_enriched_within_hours,
        ):
            skipped += 1
            continue

        try:
            job = repo.create_job(
                job_type="run_enrichment_pipeline",
                entity_kind=entity_kind,
                entity_id=entity_id_str,
                target_url=target_url,
                priority=payload.priority,
                schema_version="v1",
                freshness_bucket=job_freshness_bucket,
                input_json={
                    "entity_kind": entity_kind,
                    "entity_id": entity_id_str,
                    "entity_name": entity_name or "",
                    "category": category,
                    "website_hint": str(website_url) if website_url else None,
                },
            )
        except IntegrityError:
            db.rollback()
            skipped += 1
            continue

        run_enrichment_pipeline.apply_async(
            args=[str(job.id)],
            queue=f"pipeline.{payload.priority}",
        )
        queued += 1
        db.commit()

    # Individual jobs committed in-loop; nothing left at end.

    return {
        "entity_kind": entity_kind,
        "category": category,
        "total": len(rows),
        "queued": queued,
        "skipped": skipped,
        "message": (
            f"Queued {queued} {entity_kind} enrichment jobs. "
            f"Skipped {skipped} (recently enriched or already queued)."
        ),
    }
