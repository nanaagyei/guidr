"""Comprehensive data collection batch script."""
import argparse
import asyncio
import logging
import time
from typing import Dict, List

from src.config import settings
from src.db import SessionLocal
from src.models.institution import Institution
from src.models.program import Program
from src.scrapers.schools.multi_source_fetcher import MultiSourceFetcher
from src.scrapers.schools.comprehensive_collector import ComprehensiveSchoolCollector
from src.scrapers.agents.program_discovery_agent import ProgramDiscoveryAgent
from src.scrapers.agents.program_collection_agent import ProgramCollectionAgent
from src.services.data_ingestion import DataIngestionService
from src.services.data_validator import (
    validate_institution,
    validate_program,
    calculate_completeness_score_institution,
    calculate_completeness_score_program,
)
from src.utils.data_quality import get_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def collect_all_data(
    max_schools: int = 100,
    max_programs_per_school: int = 20,
    skip_existing: bool = True
) -> Dict:
    """
    Full workflow for comprehensive data collection.
    
    Args:
        max_schools: Maximum number of schools to process
        max_programs_per_school: Maximum programs per school
        skip_existing: Skip schools that already have programs
        
    Returns:
        Summary of collection results
    """
    db = SessionLocal()
    tracker = get_tracker()
    
    try:
        results = {
            "schools_discovered": 0,
            "schools_collected": 0,
            "programs_discovered": 0,
            "programs_collected": 0,
            "errors": [],
        }
        
        # Step 1: Fetch top schools from multiple sources
        logger.info(f"Step 1: Fetching top {max_schools} schools from multiple sources...")
        fetcher = MultiSourceFetcher()
        schools = await fetcher.fetch_all_schools(limit=max_schools)
        results["schools_discovered"] = len(schools)
        logger.info(f"Discovered {len(schools)} schools")
        
        # Step 2: For each school, collect comprehensive data
        logger.info("Step 2: Collecting comprehensive school data...")
        collector = ComprehensiveSchoolCollector()
        service = DataIngestionService(db)
        
        # Get delay settings
        school_delay = getattr(settings, 'scraper_delay_seconds', 2.0) or 2.0
        program_delay = getattr(settings, 'program_delay_seconds', 1.0) or 1.0
        
        for i, school_seed in enumerate(schools[:max_schools], 1):
            try:
                logger.info(f"Processing school {i}/{len(schools)}: {school_seed.name}")
                
                # Rate limiting: delay between schools
                if i > 1:
                    await asyncio.sleep(school_delay)
                
                # Check if school already exists
                existing = db.query(Institution).filter(
                    Institution.name == school_seed.name
                ).first()
                
                if existing and skip_existing:
                    # Check if it already has programs
                    program_count = db.query(Program).filter(
                        Program.institution_id == existing.id
                    ).count()
                    if program_count > 0:
                        logger.info(f"  Skipping {school_seed.name} (already has {program_count} programs)")
                        continue
                    institution = existing
                else:
                    # Validate and create institution
                    try:
                        validate_institution(school_seed)
                        institution = service.ingest_institution(school_seed)
                        db.commit()
                    except Exception as e:
                        logger.warning(f"  Failed to create institution: {e}")
                        continue
                
                # Collect comprehensive school data
                try:
                    school_data = await collector.collect_school_data(
                        institution.name,
                        institution.website_url
                    )
                    
                    # Update institution with collected data
                    # Note: Institution model doesn't have description field yet
                    # If you add it, uncomment this:
                    # if school_data.get("description"):
                    #     institution.description = school_data["description"]
                    
                    # Calculate completeness score
                    completeness = calculate_completeness_score_institution(school_seed)
                    institution.data_completeness_score = completeness
                    tracker.record_completeness_score(completeness)
                    
                    db.commit()
                    results["schools_collected"] += 1
                    tracker.record_extraction("comprehensive_collector", True)
                except Exception as e:
                    logger.error(f"  Error collecting school data: {e}")
                    tracker.record_extraction("comprehensive_collector", False, error_message=str(e))
                    results["errors"].append(f"School collection error for {school_seed.name}: {e}")
                
                # Step 3: Discover programs
                if institution.website_url:
                    logger.info(f"  Discovering programs for {institution.name}...")
                    discovery_agent = ProgramDiscoveryAgent()
                    
                    try:
                        program_urls = await discovery_agent.discover_programs(
                            institution.name,
                            institution.website_url
                        )
                        results["programs_discovered"] += len(program_urls)
                        logger.info(f"  Found {len(program_urls)} programs")
                        
                        await discovery_agent.close()
                    except Exception as e:
                        logger.error(f"  Error discovering programs: {e}")
                        results["errors"].append(f"Program discovery error for {institution.name}: {e}")
                        program_urls = []
                    
                    # Step 4: Collect program data
                    if program_urls:
                        logger.info(f"  Collecting data for {min(len(program_urls), max_programs_per_school)} programs...")
                        collection_agent = ProgramCollectionAgent()
                        
                        for j, program_url in enumerate(program_urls[:max_programs_per_school], 1):
                            try:
                                logger.info(f"    Program {j}/{min(len(program_urls), max_programs_per_school)}: {program_url}")
                                
                                # Rate limiting: delay between programs
                                if j > 1:
                                    await asyncio.sleep(program_delay)
                                
                                program_seed = await collection_agent.collect_program_data(
                                    program_url,
                                    institution
                                )
                                
                                # Validate program
                                try:
                                    validate_program(program_seed)
                                    
                                    # Check if program already exists
                                    # Ensure we're using the UUID properly
                                    from uuid import UUID
                                    institution_uuid = institution.id if isinstance(institution.id, UUID) else UUID(str(institution.id))
                                    
                                    existing_program = db.query(Program).filter(
                                        Program.institution_id == institution_uuid,
                                        Program.name == program_seed.name
                                    ).first()
                                    
                                    if existing_program:
                                        # Update existing
                                        for key, value in program_seed.__dict__.items():
                                            if value and hasattr(existing_program, key):
                                                setattr(existing_program, key, value)
                                        program = existing_program
                                    else:
                                        # Create new
                                        program = service.ingest_program(program_seed, institution.id)
                                    
                                    # Calculate completeness score
                                    completeness = calculate_completeness_score_program(program_seed)
                                    program.data_completeness_score = completeness
                                    tracker.record_completeness_score(completeness)
                                    
                                    db.commit()
                                    results["programs_collected"] += 1
                                    tracker.record_extraction("program_collection_agent", True)
                                    
                                except Exception as e:
                                    logger.warning(f"      Validation failed: {e}")
                                    tracker.record_validation_failure(str(e))
                                    db.rollback()
                                    
                            except Exception as e:
                                logger.error(f"      Error collecting program data: {e}")
                                tracker.record_extraction("program_collection_agent", False, error_message=str(e))
                                results["errors"].append(f"Program collection error for {program_url}: {e}")
                        
                        await collection_agent.close()
                
            except Exception as e:
                logger.error(f"Error processing school {school_seed.name}: {e}")
                results["errors"].append(f"School processing error for {school_seed.name}: {e}")
        
        await collector.close()
        
        # Step 5: Generate embeddings (optional, can be done separately)
        logger.info("Step 5: Data collection complete. Embeddings can be generated separately.")
        
        # Step 6: Get quality metrics summary
        quality_summary = tracker.get_summary()
        results["quality_metrics"] = quality_summary
        
        logger.info("=" * 60)
        logger.info("Collection Summary:")
        logger.info(f"  Schools discovered: {results['schools_discovered']}")
        logger.info(f"  Schools collected: {results['schools_collected']}")
        logger.info(f"  Programs discovered: {results['programs_discovered']}")
        logger.info(f"  Programs collected: {results['programs_collected']}")
        logger.info(f"  Overall success rate: {quality_summary.get('overall_success_rate', 0):.2%}")
        logger.info(f"  Average completeness: {quality_summary.get('average_completeness_score', 0):.1f}")
        logger.info(f"  Errors: {len(results['errors'])}")
        logger.info("=" * 60)
        
        return results
        
    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive data collection")
    parser.add_argument("--max-schools", type=int, default=100, help="Maximum schools to process")
    parser.add_argument("--max-programs", type=int, default=20, help="Maximum programs per school")
    parser.add_argument("--skip-existing", action="store_true", help="Skip schools with existing programs")
    
    args = parser.parse_args()
    
    # Run async workflow
    results = asyncio.run(collect_all_data(
        max_schools=args.max_schools,
        max_programs_per_school=args.max_programs,
        skip_existing=args.skip_existing
    ))
    
    return results


if __name__ == "__main__":
    main()

