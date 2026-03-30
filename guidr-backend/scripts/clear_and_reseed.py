#!/usr/bin/env python
"""
Clear old school data and reseed with curated graduate schools.

This script:
1. Removes all existing institutions and programs
2. Seeds curated top graduate schools
3. Reindexes Meilisearch

Usage:
    python scripts/clear_and_reseed.py
    python scripts/clear_and_reseed.py --keep-users  # Keep user data
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db import SessionLocal
from src.models.institution import Institution
from src.models.program import Program
from src.services.data_ingestion import DataIngestionService
from src.services.search_service import search_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def clear_institutions_and_programs(db):
    """Remove all institutions and programs from database."""
    logger.info("Clearing existing programs...")
    program_count = db.query(Program).count()
    db.query(Program).delete()
    logger.info(f"  Deleted {program_count} programs")
    
    logger.info("Clearing existing institutions...")
    institution_count = db.query(Institution).count()
    db.query(Institution).delete()
    logger.info(f"  Deleted {institution_count} institutions")
    
    db.commit()
    logger.info("Database cleared successfully")


def clear_search_indexes():
    """Clear Meilisearch indexes."""
    logger.info("Clearing Meilisearch indexes...")
    try:
        search_service.clear_all_indexes()
        logger.info("  Meilisearch indexes cleared")
    except Exception as e:
        logger.warning(f"  Could not clear Meilisearch indexes: {e}")


def seed_curated_schools(db):
    """Seed curated top graduate schools."""
    logger.info("Seeding curated top graduate schools...")
    service = DataIngestionService(db)
    result = service.ingest_top_graduate_schools()
    logger.info(f"  Inserted {result.get('inserted', 0)} schools")
    return result


def reindex_search(db):
    """Reindex all data in Meilisearch."""
    logger.info("Reindexing Meilisearch...")
    service = DataIngestionService(db)
    result = service.reindex_search()
    logger.info(f"  Indexed {result.get('institutions', 0)} institutions, {result.get('programs', 0)} programs")
    return result


def main():
    parser = argparse.ArgumentParser(description="Clear and reseed database with curated graduate schools")
    parser.add_argument("--keep-users", action="store_true", help="Keep user-related data")
    parser.add_argument("--skip-clear", action="store_true", help="Skip clearing (just add new schools)")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if not args.skip_clear:
            # Clear old data
            clear_institutions_and_programs(db)
            clear_search_indexes()
        
        # Seed new data
        seed_curated_schools(db)
        
        # Reindex
        reindex_search(db)
        
        # Show summary
        final_inst_count = db.query(Institution).count()
        final_prog_count = db.query(Program).count()
        
        logger.info("\n" + "="*50)
        logger.info("RESEED COMPLETE")
        logger.info("="*50)
        logger.info(f"Institutions: {final_inst_count}")
        logger.info(f"Programs: {final_prog_count}")
        logger.info("="*50)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

