"""Celery tasks for scraping + ingestion."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

from src.db import SessionLocal
from src.services.data_ingestion import DataIngestionService
from src.workers.celery_app import celery_app

# Import pipeline tasks so they are registered with the Celery app
import src.pipeline.tasks.scrape_tasks  # noqa: F401
import src.pipeline.tasks.pipeline_tasks  # noqa: F401

logger = logging.getLogger(__name__)


@celery_app.task(name="ingestion.ipeds")
def ingest_ipeds_task(year: str = "2022", limit: int | None = None):
    """Ingest institutions from IPEDS data."""
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        return service.ingest_ipeds(year=year, limit=limit)
    finally:
        db.close()


@celery_app.task(name="ingestion.scorecard")
def enrich_scorecard_task():
    """Enrich institutions with College Scorecard data."""
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        return service.enrich_with_scorecard()
    finally:
        db.close()


@celery_app.task(name="ingestion.load_scorecard_schools")
def load_graduate_schools_from_scorecard_task(
    state: Optional[str] = None,
    limit: Optional[int] = None,
):
    """Load graduate schools from College Scorecard API (bulk).

    Creates/updates Institution records for all US graduate-granting schools.
    """
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        return service.load_graduate_schools_from_scorecard(state=state, limit=limit)
    finally:
        db.close()


@celery_app.task(name="search.reindex")
def reindex_search_task():
    """Reindex all data in Meilisearch."""
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        return service.reindex_search()
    finally:
        db.close()


@celery_app.task(name="scrape.institution_programs", bind=True, max_retries=3)
def scrape_institution_programs_task(
    self,
    institution_id: str,
    institution_url: str,
    max_programs: int = 20
) -> Dict:
    """
    Scrape programs for a single institution.

    Args:
        institution_id: UUID of the institution
        institution_url: Website URL to scrape
        max_programs: Maximum programs to scrape

    Returns:
        Dict with results summary
    """
    from src.scrapers.agents.school_scraper_agent import SchoolScraperAgent
    from src.models.institution import Institution
    from src.models.program import Program

    db = SessionLocal()
    agent = SchoolScraperAgent()

    try:
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            programs_data = loop.run_until_complete(
                agent.scrape_institution_programs(institution_url, max_programs)
            )
        finally:
            loop.run_until_complete(agent.close())
            loop.close()

        # Save to database
        inst_uuid = UUID(institution_id)
        saved_count = 0

        for prog_data in programs_data:
            if not prog_data.get("name"):
                continue

            # Check if program already exists
            existing = db.query(Program).filter(
                Program.institution_id == inst_uuid,
                Program.name == prog_data["name"]
            ).first()

            if existing:
                # Update existing
                for key, value in prog_data.items():
                    if value and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new - default to 'unknown' if degree_level not detected
                degree_level = prog_data.get("degree_level") or "unknown"
                program = Program(
                    institution_id=inst_uuid,
                    name=prog_data.get("name"),
                    degree_level=degree_level,
                    field_of_study=prog_data.get("field_of_study"),
                    description=prog_data.get("description"),
                    website_url=prog_data.get("source_url"),
                    data_source="web_scrape",
                )
                db.add(program)
                saved_count += 1

        db.commit()

        logger.info(f"Saved {saved_count} programs for institution {institution_id}")
        return {
            "institution_id": institution_id,
            "programs_found": len(programs_data),
            "programs_saved": saved_count,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error scraping {institution_url}: {e}")
        db.rollback()

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(name="scrape.batch_institutions")
def batch_scrape_programs_task(
    institution_ids: List[str],
    max_programs_per_institution: int = 15
) -> Dict:
    """
    Batch scrape programs for multiple institutions.

    Args:
        institution_ids: List of institution UUIDs
        max_programs_per_institution: Max programs to scrape per school

    Returns:
        Summary of batch results
    """
    from src.models.institution import Institution

    db = SessionLocal()
    results = {"queued": 0, "failed": 0, "skipped": 0}

    try:
        for inst_id in institution_ids:
            inst = db.query(Institution).filter(
                Institution.id == UUID(inst_id)
            ).first()

            if not inst or not inst.website_url:
                results["skipped"] += 1
                continue

            try:
                # Queue individual scraping task
                scrape_institution_programs_task.delay(
                    institution_id=str(inst.id),
                    institution_url=inst.website_url,
                    max_programs=max_programs_per_institution
                )
                results["queued"] += 1
            except Exception as e:
                logger.error(f"Failed to queue scrape for {inst.name}: {e}")
                results["failed"] += 1

        return results
    finally:
        db.close()


@celery_app.task(name="document.process", bind=True, max_retries=3)
def process_document_task(self, document_id: str) -> Dict:
    """
    Process an uploaded document (transcript, resume, etc.).

    Args:
        document_id: UUID of the document

    Returns:
        Processing result
    """
    from src.workers.document_processor import process_document

    try:
        process_document(document_id)
        return {"document_id": document_id, "status": "success"}
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@celery_app.task(name="embeddings.generate_batch")
def generate_embeddings_batch_task(
    entity_type: str,
    entity_ids: List[str]
) -> Dict:
    """
    Generate embeddings for a batch of entities.

    Args:
        entity_type: "program" or "institution"
        entity_ids: List of UUIDs

    Returns:
        Summary of generation results
    """
    from src.services.embedding_service import EmbeddingService
    from src.models.institution import Institution
    from src.models.program import Program

    db = SessionLocal()
    embedding_service = EmbeddingService()

    try:
        success_count = 0

        if entity_type == "program":
            for prog_id in entity_ids:
                program = db.query(Program).filter(Program.id == UUID(prog_id)).first()
                if program:
                    embedding = embedding_service.generate_program_embedding(program)
                    if embedding:
                        program.embedding = embedding
                        success_count += 1

        elif entity_type == "institution":
            for inst_id in entity_ids:
                institution = db.query(Institution).filter(Institution.id == UUID(inst_id)).first()
                if institution:
                    embedding = embedding_service.generate_institution_embedding(institution)
                    if embedding:
                        institution.embedding = embedding
                        success_count += 1

        db.commit()
        return {
            "entity_type": entity_type,
            "total": len(entity_ids),
            "success": success_count
        }
    finally:
        db.close()


@celery_app.task(name="collect.school_comprehensive", bind=True, max_retries=3)
def collect_school_comprehensive_task(self, institution_id: str) -> Dict:
    """
    Collect all school data using multiple methods.

    Args:
        institution_id: UUID of the institution

    Returns:
        Dict with collected data summary
    """
    from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector
    from src.models.institution import Institution

    db = SessionLocal()
    collector = ComprehensiveSchoolCollector()

    try:
        institution = db.query(Institution).filter(Institution.id == UUID(institution_id)).first()
        if not institution:
            return {"error": "Institution not found", "institution_id": institution_id}

        # Run async collection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            data = loop.run_until_complete(
                collector.collect_school_data(institution.name, institution.website_url)
            )
        finally:
            loop.run_until_complete(collector.close())
            loop.close()

        # Update institution with collected data
        if data.get("description"):
            institution.description = data["description"]
        if data.get("acceptance_rate"):
            # Note: Institution model may need acceptance_rate field
            pass

        db.commit()

        return {
            "institution_id": institution_id,
            "status": "success",
            "data_collected": list(data.keys())
        }

    except Exception as e:
        logger.error(f"Error collecting school data for {institution_id}: {e}")
        db.rollback()
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(name="discover.programs", bind=True, max_retries=3)
def discover_programs_task(self, institution_id: str) -> Dict:
    """
    Discover all programs for a school.

    Args:
        institution_id: UUID of the institution

    Returns:
        Dict with discovered program URLs
    """
    from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent
    from src.models.institution import Institution

    db = SessionLocal()
    agent = ProgramDiscoveryAgent()

    try:
        institution = db.query(Institution).filter(Institution.id == UUID(institution_id)).first()
        if not institution or not institution.website_url:
            return {"error": "Institution not found or no website URL", "institution_id": institution_id}

        # Run async discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            program_urls = loop.run_until_complete(
                agent.discover_programs(institution.name, institution.website_url)
            )
        finally:
            loop.run_until_complete(agent.close())
            loop.close()

        return {
            "institution_id": institution_id,
            "program_urls": program_urls,
            "count": len(program_urls),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error discovering programs for {institution_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@celery_app.task(name="collect.program_comprehensive", bind=True, max_retries=3)
def collect_program_comprehensive_task(
    self,
    program_url: str,
    institution_id: str
) -> Dict:
    """
    Collect comprehensive program data.

    Args:
        program_url: URL of the program page
        institution_id: UUID of the institution

    Returns:
        Dict with collected program data
    """
    from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent
    from src.models.institution import Institution
    from src.models.program import Program
    from src.services.data_ingestion import DataIngestionService

    db = SessionLocal()
    agent = ProgramCollectionAgent()

    try:
        institution = db.query(Institution).filter(Institution.id == UUID(institution_id)).first()
        if not institution:
            return {"error": "Institution not found", "institution_id": institution_id}

        # Run async collection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            program_seed = loop.run_until_complete(
                agent.collect_program_data(program_url, institution)
            )
        finally:
            loop.run_until_complete(agent.close())
            loop.close()

        # Save to database
        service = DataIngestionService(db)
        program = service.ingest_program(program_seed, institution.id)

        db.commit()

        return {
            "program_id": str(program.id) if program else None,
            "program_url": program_url,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error collecting program data for {program_url}: {e}")
        db.rollback()
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
