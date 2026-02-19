#!/usr/bin/env python
"""
Batch seeding script for Guidr database.

This script performs a complete data seeding workflow:
1. Ingest institutions from IPEDS
2. Enrich with College Scorecard data
3. Fetch top schools from additional APIs
4. Scrape programs from institution websites
5. Generate embeddings
6. Index in Meilisearch

Usage:
    python scripts/batch_seed.py --all
    python scripts/batch_seed.py --ipeds --limit 500
    python scripts/batch_seed.py --programs --max-per-school 10
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.db import SessionLocal
from src.models.institution import Institution
from src.models.program import Program
from src.services.data_ingestion import DataIngestionService
from src.services.search_service import search_service
from src.services.embedding_service import EmbeddingService
from src.scrapers.schools.top_schools import TopSchoolsFetcher
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper, TOP_GRADUATE_SCHOOLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def seed_ipeds(db: Session, year: str = "2022", limit: int | None = None):
    """Seed institutions from IPEDS data."""
    logger.info(f"Starting IPEDS ingestion (year={year}, limit={limit})")
    service = DataIngestionService(db)
    result = service.ingest_ipeds(year=year, limit=limit)
    logger.info(f"IPEDS ingestion complete: {result}")
    return result


def enrich_scorecard(db: Session):
    """Enrich institutions with College Scorecard data."""
    logger.info("Starting College Scorecard enrichment")
    service = DataIngestionService(db)
    result = service.enrich_with_scorecard()
    logger.info(f"Scorecard enrichment complete: {result}")
    return result


def seed_top_schools(db: Session):
    """Fetch and seed top schools from QS/THE rankings."""
    logger.info("Fetching top schools from rankings APIs")
    fetcher = TopSchoolsFetcher()
    
    try:
        top_schools = fetcher.fetch_all_top_schools()
        logger.info(f"Found {len(top_schools)} top schools from rankings")
        
        created = 0
        updated = 0
        
        for school in top_schools:
            # Check if already exists
            existing = db.query(Institution).filter(
                Institution.name == school.name,
                Institution.country == school.country
            ).first()
            
            if existing:
                # Update ranking info
                if school.qs_rank and (not existing.qs_world_rank or existing.qs_world_rank > school.qs_rank):
                    existing.qs_world_rank = school.qs_rank
                if school.the_rank and (not existing.the_world_rank or existing.the_world_rank > school.the_rank):
                    existing.the_world_rank = school.the_rank
                updated += 1
            else:
                # Create new
                institution = Institution(
                    name=school.name,
                    country=school.country,
                    city=school.city,
                    website_url=school.website_url,
                    qs_world_rank=school.qs_rank,
                    the_world_rank=school.the_rank,
                    data_source="rankings",
                )
                db.add(institution)
                created += 1
        
        db.commit()
        logger.info(f"Top schools: created {created}, updated {updated}")
        return {"created": created, "updated": updated}
    finally:
        fetcher.close()


def seed_curated_graduate_schools(db: Session, limit: int | None = None):
    """Seed curated list of top graduate schools.
    
    This uses a built-in list of top universities known for their
    graduate programs - no external API required.
    """
    logger.info("Seeding curated top graduate schools...")
    service = DataIngestionService(db)
    result = service.ingest_top_graduate_schools(limit=limit)
    logger.info(f"Curated schools ingestion complete: {result}")
    return result


def scrape_programs_firecrawl(
    db: Session,
    max_institutions: int = 10,
    max_programs_per: int = 20
):
    """Scrape programs using Firecrawl API for curated schools.
    
    This uses the Firecrawl API for intelligent scraping.
    Requires FIRECRAWL_API_KEY environment variable.
    """
    scraper = FirecrawlScraper()
    
    if not scraper.is_available():
        logger.warning("Firecrawl API key not configured. Set FIRECRAWL_API_KEY in .env")
        return {"error": "Firecrawl not configured"}
    
    logger.info(f"Scraping programs with Firecrawl for up to {max_institutions} schools")
    
    service = DataIngestionService(db)
    total_programs = 0
    
    # Use curated schools with known program URLs
    schools_to_scrape = [
        s for s in TOP_GRADUATE_SCHOOLS 
        if s.get("grad_programs_url")
    ][:max_institutions]
    
    for school_data in schools_to_scrape:
        # Find institution in DB
        institution = db.query(Institution).filter(
            Institution.name == school_data["name"]
        ).first()
        
        if not institution:
            logger.info(f"Institution {school_data['name']} not in DB, skipping")
            continue
        
        try:
            result = service.scrape_programs_with_firecrawl(
                institution_id=str(institution.id),
                programs_url=school_data["grad_programs_url"],
                max_programs=max_programs_per
            )
            total_programs += result.get("programs", 0)
            logger.info(f"  {school_data['name']}: {result.get('programs', 0)} programs")
        except Exception as e:
            logger.error(f"  Failed for {school_data['name']}: {e}")
    
    return {"total_programs": total_programs}


def scrape_programs(
    db: Session, 
    max_institutions: int = 50,
    max_programs_per: int = 15,
    use_celery: bool = False
):
    """Scrape programs from institution websites."""
    from src.scrapers.agents.school_scraper_agent import SchoolScraperAgent
    
    # Get institutions with websites that have few/no programs
    institutions = db.query(Institution).filter(
        Institution.website_url.isnot(None),
        Institution.is_deleted == False
    ).order_by(
        Institution.qs_world_rank.asc().nullslast(),
        Institution.data_completeness_score.desc()
    ).limit(max_institutions).all()
    
    logger.info(f"Will scrape programs for {len(institutions)} institutions")
    
    if use_celery:
        # Queue as Celery tasks
        from src.workers.scraper_worker import scrape_institution_programs_task
        
        for inst in institutions:
            scrape_institution_programs_task.delay(
                institution_id=str(inst.id),
                institution_url=inst.website_url,
                max_programs=max_programs_per
            )
        logger.info(f"Queued {len(institutions)} scraping tasks")
        return {"queued": len(institutions)}
    
    # Run synchronously
    agent = SchoolScraperAgent()
    total_programs = 0
    
    async def run_scraping():
        nonlocal total_programs
        try:
            for i, inst in enumerate(institutions):
                logger.info(f"[{i+1}/{len(institutions)}] Scraping {inst.name}...")
                try:
                    programs = await agent.scrape_institution_programs(
                        inst.website_url, 
                        max_programs_per
                    )
                    
                    for prog_data in programs:
                        if not prog_data.get("name"):
                            continue
                        
                        existing = db.query(Program).filter(
                            Program.institution_id == inst.id,
                            Program.name == prog_data["name"]
                        ).first()
                        
                        if not existing:
                            # Default to 'masters' if degree_level not detected
                            degree_level = prog_data.get("degree_level") or "unknown"
                            program = Program(
                                institution_id=inst.id,
                                name=prog_data.get("name"),
                                degree_level=degree_level,
                                field_of_study=prog_data.get("field_of_study"),
                                description=prog_data.get("description"),
                                website_url=prog_data.get("source_url"),
                                data_source="web_scrape",
                            )
                            db.add(program)
                            total_programs += 1
                    
                    db.commit()
                    logger.info(f"  Found {len(programs)} programs")
                    
                except Exception as e:
                    logger.error(f"  Failed: {e}")
                    db.rollback()
        finally:
            await agent.close()
    
    asyncio.run(run_scraping())
    logger.info(f"Program scraping complete: {total_programs} programs saved")
    return {"programs_saved": total_programs}


def generate_embeddings(db: Session, batch_size: int = 100):
    """Generate embeddings for all programs and institutions."""
    logger.info("Generating embeddings...")
    service = EmbeddingService()
    
    # Programs (no is_deleted filter - Program model doesn't have it)
    programs = db.query(Program).filter(
        Program.embedding.is_(None)
    ).limit(batch_size * 10).all()
    
    prog_count = 0
    for program in programs:
        embedding = service.embed_program(program)
        if embedding:
            program.embedding = embedding
            prog_count += 1
    
    # Institutions
    institutions = db.query(Institution).filter(
        Institution.embedding.is_(None),
        Institution.is_deleted == False
    ).limit(batch_size * 10).all()
    
    inst_count = 0
    for inst in institutions:
        embedding = service.embed_institution(inst)
        if embedding:
            inst.embedding = embedding
            inst_count += 1
    
    db.commit()
    logger.info(f"Generated embeddings: {prog_count} programs, {inst_count} institutions")
    return {"programs": prog_count, "institutions": inst_count}


def reindex_search(db: Session):
    """Reindex all data in Meilisearch."""
    logger.info("Reindexing Meilisearch...")
    service = DataIngestionService(db)
    result = service.reindex_search()
    logger.info(f"Reindex complete: {result}")
    return result


def run_all(
    db: Session,
    ipeds_limit: int = 500,
    top_schools: bool = True,
    scrape: bool = True,
    embeddings: bool = True,
    reindex: bool = True,
    use_firecrawl: bool = False
):
    """Run complete seeding workflow."""
    results = {}
    
    # 1. Curated Graduate Schools (always run first for best quality)
    results["curated_schools"] = seed_curated_graduate_schools(db)
    
    # 2. IPEDS (for additional US schools)
    if ipeds_limit and ipeds_limit > 0:
        results["ipeds"] = seed_ipeds(db, limit=ipeds_limit)
    
    # 3. College Scorecard
    results["scorecard"] = enrich_scorecard(db)
    
    # 4. Top Schools from Rankings
    if top_schools:
        results["top_schools"] = seed_top_schools(db)
    
    # 5. Program Scraping
    if scrape:
        if use_firecrawl:
            results["programs"] = scrape_programs_firecrawl(db, max_institutions=20, max_programs_per=20)
        else:
            results["programs"] = scrape_programs(db, max_institutions=30, max_programs_per=10)
    
    # 6. Embeddings
    if embeddings:
        results["embeddings"] = generate_embeddings(db)
    
    # 7. Reindex
    if reindex:
        results["search"] = reindex_search(db)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Batch seed Guidr database")
    parser.add_argument("--all", action="store_true", help="Run complete seeding workflow")
    parser.add_argument("--ipeds", action="store_true", help="Seed from IPEDS")
    parser.add_argument("--ipeds-year", default="2022", help="IPEDS data year")
    parser.add_argument("--limit", type=int, help="Limit number of institutions")
    parser.add_argument("--scorecard", action="store_true", help="Enrich with College Scorecard")
    parser.add_argument("--top-schools", action="store_true", help="Fetch top schools from rankings")
    parser.add_argument("--curated", action="store_true", help="Seed curated top graduate schools")
    parser.add_argument("--programs", action="store_true", help="Scrape programs")
    parser.add_argument("--max-per-school", type=int, default=15, help="Max programs per school")
    parser.add_argument("--use-celery", action="store_true", help="Use Celery for async scraping")
    parser.add_argument("--use-firecrawl", action="store_true", help="Use Firecrawl for program scraping")
    parser.add_argument("--embeddings", action="store_true", help="Generate embeddings")
    parser.add_argument("--reindex", action="store_true", help="Reindex Meilisearch")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.all:
            results = run_all(
                db, 
                ipeds_limit=args.limit or 100,  # Reduced default - curated schools are primary
                use_firecrawl=args.use_firecrawl
            )
            logger.info(f"\n=== Complete Seeding Results ===\n{results}")
        else:
            if args.curated:
                seed_curated_graduate_schools(db, limit=args.limit)
            if args.ipeds:
                seed_ipeds(db, year=args.ipeds_year, limit=args.limit)
            if args.scorecard:
                enrich_scorecard(db)
            if args.top_schools:
                seed_top_schools(db)
            if args.programs:
                if args.use_firecrawl:
                    scrape_programs_firecrawl(
                        db,
                        max_institutions=args.limit or 10,
                        max_programs_per=args.max_per_school
                    )
                else:
                    scrape_programs(
                        db, 
                        max_institutions=args.limit or 50,
                        max_programs_per=args.max_per_school,
                        use_celery=args.use_celery
                    )
            if args.embeddings:
                generate_embeddings(db)
            if args.reindex:
                reindex_search(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

