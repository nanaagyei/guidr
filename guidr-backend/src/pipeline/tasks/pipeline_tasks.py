"""High-level pipeline orchestration tasks."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import UUID

from celery import chain, group

from src.db import SessionLocal
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

STALE_DAYS = 30


@celery_app.task(name="pipeline.run_full")
def run_full_pipeline(institution_id: str) -> Dict:
    """Run the complete scraping pipeline for a single institution.

    Orchestrates overview → funding + faculty extraction in sequence.

    Args:
        institution_id: UUID of the institution.

    Returns:
        Summary of queued sub-tasks.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info(
            "Bulk scraping disabled (enable_bulk_scrape=False), skipping institution %s",
            institution_id,
        )
        return {"status": "skipped", "reason": "bulk_scrape_disabled", "institution_id": institution_id}

    from src.models.institution import Institution
    from src.models.scrape_job import ScrapeJob

    db = SessionLocal()

    try:
        institution = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not institution or not institution.website_url:
            return {"error": "Institution not found or no website URL"}

        # Mark institution as scraping
        institution.scrape_status = "scraping"
        db.commit()

        # Create a parent job to track the full pipeline
        job = ScrapeJob(
            institution_id=UUID(institution_id),
            job_type="full_pipeline",
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        # Use Celery chain: overview first, then programs + funding + faculty in parallel
        from src.pipeline.tasks.scrape_tasks import (
            extract_faculty_for_institution,
            extract_funding_for_institution,
            extract_programs_for_institution,
            scrape_overview_for_institution,
        )

        workflow = chain(
            scrape_overview_for_institution.si(institution_id),
            group(
                extract_programs_for_institution.si(institution_id),
                extract_funding_for_institution.si(institution_id),
                extract_faculty_for_institution.si(institution_id),
            ),
        )
        workflow.apply_async()

        logger.info("Full pipeline queued for %s", institution.name)
        return {
            "institution_id": institution_id,
            "job_id": str(job.id),
            "status": "queued",
        }

    finally:
        db.close()


@celery_app.task(name="pipeline.batch_scrape")
def batch_scrape_institutions(
    institution_ids: List[str],
) -> Dict:
    """Queue full pipeline runs for multiple institutions.

    Args:
        institution_ids: List of institution UUID strings.

    Returns:
        Summary with queued/skipped/failed counts.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Bulk scraping disabled (enable_bulk_scrape=False), skipping batch")
        return {"status": "skipped", "reason": "bulk_scrape_disabled", "queued": 0, "skipped": len(institution_ids), "failed": 0}

    from src.models.institution import Institution

    db = SessionLocal()
    results = {"queued": 0, "skipped": 0, "failed": 0}

    try:
        for inst_id in institution_ids:
            inst = db.query(Institution).filter(
                Institution.id == UUID(inst_id)
            ).first()

            if not inst or not inst.website_url:
                results["skipped"] += 1
                continue

            try:
                run_full_pipeline.delay(str(inst.id))
                results["queued"] += 1
            except Exception as exc:
                logger.error("Failed to queue pipeline for %s: %s", inst.name, exc)
                results["failed"] += 1

        return results
    finally:
        db.close()


@celery_app.task(name="pipeline.refresh_stale")
def refresh_stale_institutions() -> Dict:
    """Queue full pipeline for institutions not scraped in the last N days.

    Called by Celery Beat (e.g., weekly). Institutions with last_scraped_at
    older than STALE_DAYS (or never scraped) are queued for re-scraping.

    Returns:
        Dict with queued, skipped, failed counts.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Bulk scraping disabled (enable_bulk_scrape=False), skipping stale refresh")
        return {"status": "skipped", "reason": "bulk_scrape_disabled", "queued": 0, "skipped": 0, "failed": 0}

    from src.models.institution import Institution

    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
    results = {"queued": 0, "skipped": 0, "failed": 0}

    try:
        stale = (
            db.query(Institution)
            .filter(Institution.website_url.isnot(None))
            .filter(
                (Institution.last_scraped_at.is_(None))
                | (Institution.last_scraped_at < cutoff)
            )
            .limit(100)
            .all()
        )

        for inst in stale:
            try:
                run_full_pipeline.delay(str(inst.id))
                results["queued"] += 1
            except Exception as exc:
                logger.error("Failed to queue pipeline for %s: %s", inst.name, exc)
                results["failed"] += 1

        return results
    finally:
        db.close()


@celery_app.task(name="pipeline.run_orchestrator")
def run_orchestrator_pipeline(
    institution_id: str,
    category: str = "SCHOOL_OVERVIEW",
) -> Dict:
    """Run LangGraph orchestrator for an institution and category.

    Uses discovery -> fetch -> extract -> validate -> promote workflow.
    Requires langgraph to be installed.

    Args:
        institution_id: UUID of the institution.
        category: SCHOOL_OVERVIEW, PROGRAM_REQUIREMENTS, FACULTY_DIRECTORY, etc.

    Returns:
        Final state with status, confidence, progress.
    """
    from src.models.institution import Institution
    from src.pipeline.orchestrator.graph import create_orchestrator_graph

    db = SessionLocal()
    try:
        inst = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not inst:
            return {"error": "Institution not found", "institution_id": institution_id}

        graph = create_orchestrator_graph()
        initial: dict = {
            "job_id": str(institution_id),
            "entity_kind": "school",
            "entity_id": institution_id,
            "category": category,
            "entity_name": inst.name,
            "website_hint": inst.website_url,
            "known_sources": [],
        }
        run_config = {"configurable": {"thread_id": str(institution_id)}}
        result = graph.invoke(initial, config=run_config)
        return {
            "institution_id": institution_id,
            "status": result.get("status", "unknown"),
            "confidence": result.get("confidence", 0),
            "progress": result.get("progress", []),
            "error": result.get("error"),
        }
    except ImportError as exc:
        logger.warning("Orchestrator skipped (langgraph not installed): %s", exc)
        return {"error": "langgraph not installed", "institution_id": institution_id}
    except Exception as exc:
        logger.exception("Orchestrator failed for %s: %s", institution_id, exc)
        return {"error": str(exc), "institution_id": institution_id}
    finally:
        db.close()
