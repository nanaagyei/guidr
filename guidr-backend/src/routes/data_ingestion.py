"""Admin-only ingestion and pipeline endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db import get_db
from src.dependencies.auth import require_admin_user
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
    _: str = Depends(require_admin_user),
):
    service = DataIngestionService(db)
    return service.ingest_ipeds(year=payload.year, limit=payload.limit)


@router.post("/schools/scorecard")
async def trigger_scorecard_enrichment(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_user),
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
    _: str = Depends(require_admin_user),
):
    """Load graduate schools from College Scorecard API (bulk).

    Use async_run=True to queue as Celery task for large loads.
    """
    if payload.async_run:
        from src.workers.scraper_worker import load_graduate_schools_from_scorecard_task
        load_graduate_schools_from_scorecard_task.delay(
            state=payload.state,
            limit=payload.limit,
        )
        return {"message": "Scorecard load queued", "async": True}
    service = DataIngestionService(db)
    return service.load_graduate_schools_from_scorecard(
        state=payload.state,
        limit=payload.limit,
    )


@router.post("/search/reindex")
async def trigger_search_reindex(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_user),
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
    _: str = Depends(require_admin_user),
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
    _: str = Depends(require_admin_user),
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
    _: str = Depends(require_admin_user),
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
    _: str = Depends(require_admin_user),
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

