"""Celery tasks for individual scrape operations (funding, faculty, overview)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict
from uuid import UUID

from src.db import SessionLocal
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="pipeline.extract_funding", bind=True, max_retries=3)
def extract_funding_for_institution(self, institution_id: str) -> Dict:
    """Scrape and extract funding opportunities for an institution.

    Args:
        institution_id: UUID of the institution.

    Returns:
        Summary dict with counts and status.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Scraping disabled (enable_bulk_scrape=False), skipping funding for %s", institution_id)
        return {"status": "skipped", "reason": "scraping_disabled", "institution_id": institution_id}

    from src.models.institution import Institution
    from src.models.funding_opportunity import FundingOpportunity
    from src.models.scrape_job import ScrapeJob
    from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient
    from src.pipeline.clients.storage_client import DataLakeStorageClient
    from src.pipeline.extractors.funding_extractor import FundingExtractor

    db = SessionLocal()
    client = EnhancedFirecrawlClient()
    extractor = FundingExtractor()
    storage = DataLakeStorageClient()

    # Create scrape job
    job = ScrapeJob(
        institution_id=UUID(institution_id),
        job_type="funding",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        institution = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not institution or not institution.website_url:
            job.status = "failed"
            job.error_message = "Institution not found or no website URL"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": job.error_message}

        # Scrape funding pages
        pages = client.scrape_funding_pages(institution.website_url)
        job.pages_scraped = len(pages)

        # Store raw data
        storage.store_json(
            institution_id, "funding", "raw_pages.json",
            [{"source_url": p.get("source_url"), "markdown_length": len(p.get("markdown", ""))} for p in pages],
        )

        # Extract funding items from each page
        saved_count = 0
        for page in pages:
            markdown = page.get("markdown", "")
            source_url = page.get("source_url")
            items = extractor.extract_from_markdown(markdown, source_url)

            for item in items:
                funding = FundingOpportunity(
                    institution_id=UUID(institution_id),
                    name=item.name,
                    funding_type=item.funding_type.value,
                    amount_min=item.amount_min,
                    amount_max=item.amount_max,
                    amount_period=item.amount_period.value if item.amount_period else None,
                    deadline=item.deadline,
                    eligibility_criteria=item.eligibility_criteria,
                    description=item.description,
                    website_url=item.website_url,
                    is_need_based=item.is_need_based,
                    is_merit_based=item.is_merit_based,
                    covers_tuition=item.covers_tuition,
                    covers_stipend=item.covers_stipend,
                    source_url=item.source_url,
                    data_source="pipeline_scrape",
                )
                db.add(funding)
                saved_count += 1

        job.status = "completed"
        job.items_extracted = saved_count
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info("Extracted %d funding items for %s", saved_count, institution.name)
        return {
            "institution_id": institution_id,
            "pages_scraped": len(pages),
            "items_extracted": saved_count,
            "status": "success",
        }

    except Exception as exc:
        logger.error("Funding extraction failed for %s: %s", institution_id, exc)
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.completed_at = datetime.utcnow()
        db.commit()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        client.close()
        db.close()


@celery_app.task(name="pipeline.extract_faculty", bind=True, max_retries=3)
def extract_faculty_for_institution(self, institution_id: str) -> Dict:
    """Scrape and extract faculty data for an institution.

    Args:
        institution_id: UUID of the institution.

    Returns:
        Summary dict.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Scraping disabled (enable_bulk_scrape=False), skipping faculty for %s", institution_id)
        return {"status": "skipped", "reason": "scraping_disabled", "institution_id": institution_id}

    from src.models.institution import Institution
    from src.models.professor import Professor
    from src.models.scrape_job import ScrapeJob
    from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient
    from src.pipeline.clients.storage_client import DataLakeStorageClient
    from src.pipeline.extractors.faculty_extractor import FacultyExtractor

    db = SessionLocal()
    client = EnhancedFirecrawlClient()
    extractor = FacultyExtractor()
    storage = DataLakeStorageClient()

    job = ScrapeJob(
        institution_id=UUID(institution_id),
        job_type="faculty",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        institution = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not institution or not institution.website_url:
            job.status = "failed"
            job.error_message = "Institution not found or no website URL"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": job.error_message}

        pages = client.scrape_faculty_pages(institution.website_url)
        job.pages_scraped = len(pages)

        storage.store_json(
            institution_id, "faculty", "raw_pages.json",
            [{"source_url": p.get("source_url"), "markdown_length": len(p.get("markdown", ""))} for p in pages],
        )

        saved_count = 0
        for page in pages:
            markdown = page.get("markdown", "")
            source_url = page.get("source_url")
            professors = extractor.extract_from_markdown(markdown, source_url)

            for prof_data in professors:
                # Check for existing professor by name at this institution
                existing = db.query(Professor).filter(
                    Professor.institution_id == UUID(institution_id),
                    Professor.full_name == prof_data.full_name,
                ).first()

                if existing:
                    # Update fields that were previously null
                    if prof_data.title and not existing.title:
                        existing.title = prof_data.title
                    if prof_data.email and not existing.email:
                        existing.email = prof_data.email
                    if prof_data.interests_tags and not existing.interests_tags:
                        existing.interests_tags = prof_data.interests_tags
                    existing.last_scraped_at = datetime.utcnow()
                else:
                    professor = Professor(
                        institution_id=UUID(institution_id),
                        full_name=prof_data.full_name,
                        title=prof_data.title,
                        email=prof_data.email,
                        personal_page_url=prof_data.personal_page_url,
                        scholar_profile_url=prof_data.scholar_profile_url,
                        interests_tags=prof_data.interests_tags,
                        is_accepting_students=prof_data.is_accepting_students,
                        last_scraped_at=datetime.utcnow(),
                    )
                    db.add(professor)
                    saved_count += 1

        job.status = "completed"
        job.items_extracted = saved_count
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info("Extracted %d faculty for %s", saved_count, institution.name)
        return {
            "institution_id": institution_id,
            "pages_scraped": len(pages),
            "items_extracted": saved_count,
            "status": "success",
        }

    except Exception as exc:
        logger.error("Faculty extraction failed for %s: %s", institution_id, exc)
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.completed_at = datetime.utcnow()
        db.commit()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        client.close()
        db.close()


@celery_app.task(name="pipeline.extract_programs", bind=True, max_retries=3)
def extract_programs_for_institution(self, institution_id: str) -> Dict:
    """Scrape and extract graduate programs for an institution.

    Args:
        institution_id: UUID of the institution.

    Returns:
        Summary dict.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Scraping disabled (enable_bulk_scrape=False), skipping programs for %s", institution_id)
        return {"status": "skipped", "reason": "scraping_disabled", "institution_id": institution_id}

    from src.models.institution import Institution
    from src.models.program import Program
    from src.models.scrape_job import ScrapeJob
    from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient
    from src.pipeline.clients.storage_client import DataLakeStorageClient
    from src.pipeline.extractors.program_extractor import ProgramExtractor

    db = SessionLocal()
    client = EnhancedFirecrawlClient()
    extractor = ProgramExtractor()
    storage = DataLakeStorageClient()

    job = ScrapeJob(
        institution_id=UUID(institution_id),
        job_type="programs",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        institution = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not institution or not institution.website_url:
            job.status = "failed"
            job.error_message = "Institution not found or no website URL"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": job.error_message}

        pages = client.scrape_program_pages(institution.website_url, limit=15)
        job.pages_scraped = len(pages)

        storage.store_json(
            institution_id, "programs", "raw_pages.json",
            [{"source_url": p.get("source_url"), "markdown_length": len(p.get("markdown", ""))} for p in pages],
        )

        saved_count = 0
        inst_uuid = UUID(institution_id)
        for page in pages:
            markdown = page.get("markdown", "")
            source_url = page.get("source_url")
            programs = extractor.extract_from_markdown(markdown, source_url)

            for prog_data in programs:
                existing = db.query(Program).filter(
                    Program.institution_id == inst_uuid,
                    Program.name == prog_data.name,
                ).first()
                if existing:
                    if prog_data.duration_months and not existing.duration_months:
                        existing.duration_months = prog_data.duration_months
                    if prog_data.gre_required is not None and existing.gre_required is None:
                        existing.gre_required = prog_data.gre_required
                    if prog_data.minimum_gpa and not existing.minimum_gpa:
                        existing.minimum_gpa = prog_data.minimum_gpa
                    existing.last_scraped_at = datetime.utcnow()
                else:
                    program = Program(
                        institution_id=inst_uuid,
                        name=prog_data.name,
                        degree_level=prog_data.degree_level or "masters",
                        field_of_study=prog_data.field_of_study,
                        description=prog_data.description,
                        website_url=prog_data.website_url,
                        duration_months=prog_data.duration_months,
                        gre_required=prog_data.gre_required,
                        minimum_gpa=prog_data.minimum_gpa,
                        application_deadline_primary=prog_data.application_deadline_primary,
                        tuition_estimate_per_year=prog_data.tuition_estimate_per_year,
                        last_scraped_at=datetime.utcnow(),
                        data_source="pipeline_scrape",
                    )
                    db.add(program)
                    saved_count += 1

        job.status = "completed"
        job.items_extracted = saved_count
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info("Extracted %d programs for %s", saved_count, institution.name)
        return {
            "institution_id": institution_id,
            "pages_scraped": len(pages),
            "items_extracted": saved_count,
            "status": "success",
        }

    except Exception as exc:
        logger.error("Program extraction failed for %s: %s", institution_id, exc)
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.completed_at = datetime.utcnow()
        db.commit()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        client.close()
        db.close()


@celery_app.task(name="pipeline.scrape_overview", bind=True, max_retries=3)
def scrape_overview_for_institution(self, institution_id: str) -> Dict:
    """Scrape overview/about data for an institution and update the record.

    Args:
        institution_id: UUID of the institution.

    Returns:
        Summary dict.
    """
    from src.config import settings

    if not settings.enable_bulk_scrape:
        logger.info("Scraping disabled (enable_bulk_scrape=False), skipping overview for %s", institution_id)
        return {"status": "skipped", "reason": "scraping_disabled", "institution_id": institution_id}

    from src.models.institution import Institution
    from src.models.scrape_job import ScrapeJob
    from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient
    from src.pipeline.clients.storage_client import DataLakeStorageClient
    from src.pipeline.extractors.overview_extractor import OverviewExtractor

    db = SessionLocal()
    client = EnhancedFirecrawlClient()
    extractor = OverviewExtractor()
    storage = DataLakeStorageClient()

    job = ScrapeJob(
        institution_id=UUID(institution_id),
        job_type="overview",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        institution = db.query(Institution).filter(
            Institution.id == UUID(institution_id)
        ).first()
        if not institution or not institution.website_url:
            job.status = "failed"
            job.error_message = "Institution not found or no website URL"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": job.error_message}

        page = client.scrape_overview_page(institution.website_url)
        if not page:
            job.status = "failed"
            job.error_message = "Could not scrape overview page"
            job.completed_at = datetime.utcnow()
            db.commit()
            return {"error": job.error_message}

        job.pages_scraped = 1

        # Store raw data
        storage.store_text(
            institution_id, "overview", "overview.md", page.get("markdown", ""),
        )

        overview = extractor.extract_from_markdown(page.get("markdown", ""))

        # Update institution fields (only overwrite if we have new data)
        if overview.description and not institution.description:
            institution.description = overview.description
        if overview.acceptance_rate is not None:
            institution.acceptance_rate = overview.acceptance_rate
        if overview.enrollment_total is not None:
            institution.enrollment_total = overview.enrollment_total
        if overview.grad_enrollment is not None:
            institution.grad_enrollment = overview.grad_enrollment
        if overview.campus_setting and not institution.campus_setting:
            institution.campus_setting = overview.campus_setting
        if overview.academic_calendar and not institution.academic_calendar:
            institution.academic_calendar = overview.academic_calendar

        institution.last_scraped_at = datetime.utcnow()
        institution.scrape_status = "completed"

        job.status = "completed"
        job.items_extracted = 1
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info("Scraped overview for %s", institution.name)
        return {
            "institution_id": institution_id,
            "status": "success",
            "fields_updated": {
                k: v for k, v in overview.model_dump().items() if v is not None
            },
        }

    except Exception as exc:
        logger.error("Overview scrape failed for %s: %s", institution_id, exc)
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.completed_at = datetime.utcnow()
        db.commit()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        client.close()
        db.close()
