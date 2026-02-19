#!/usr/bin/env python
"""
Reset pipeline data: remove all schools, programs, faculty, funding, and scrape jobs.

This script deletes all previously scraped data in FK-safe order. User data
(users, profiles, recommendation sessions, essays) is preserved. Essay
target_program_id is set to NULL.

Deletion order (respecting foreign keys):
  RecommendationResult -> OutreachEmail -> ProfessorResearchTag -> ProfessorProgram
  -> FundingOpportunity -> Professor -> ProgramTag -> Essay (null target) -> Program
  -> ScrapeJob -> Institution

After DB cleanup, Meilisearch indexes (institutions, programs, funding) are cleared.

Object storage (MinIO/S3): Raw scrape artifacts under raw/ prefix are NOT
automatically purged. Path pattern: raw/{YYYY}/{MM}/{DD}/{institution_id}/{job_type}/*

Usage:
    python scripts/reset_pipeline_data.py --dry-run   # Preview without changes
    python scripts/reset_pipeline_data.py --yes       # Skip confirmation prompt
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db import SessionLocal

# Ensure Essay-related models are loaded before querying (fixes mapper config)
from src.models.essay_version import EssayVersion  # noqa: F401
from src.models.essay_review import EssayReview  # noqa: F401

from src.models.recommendation_result import RecommendationResult
from src.models.outreach_email import OutreachEmail
from src.models.professor_research_tag import ProfessorResearchTag
from src.models.professor_program import ProfessorProgram
from src.models.funding_opportunity import FundingOpportunity
from src.models.professor import Professor
from src.models.program_tag import ProgramTag
from src.models.essay import Essay
from src.models.program import Program
from src.models.scrape_job import ScrapeJob
from src.models.institution import Institution
from src.services.search_service import search_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def get_counts(db) -> dict:
    """Return row counts for all affected tables."""
    models = [
        ("recommendation_results", RecommendationResult),
        ("outreach_emails", OutreachEmail),
        ("professor_research_tags", ProfessorResearchTag),
        ("professor_programs", ProfessorProgram),
        ("funding_opportunities", FundingOpportunity),
        ("professors", Professor),
        ("program_tags", ProgramTag),
        ("essays_with_program", None),  # Special: count where target_program_id IS NOT NULL
        ("programs", Program),
        ("scrape_jobs", ScrapeJob),
        ("institutions", Institution),
    ]
    counts = {}
    for name, model in models:
        if name == "essays_with_program":
            counts[name] = db.query(Essay).filter(Essay.target_program_id.isnot(None)).count()
        else:
            counts[name] = db.query(model).count()
    return counts


def reset_pipeline_data(db, dry_run: bool = False) -> dict:
    """Delete all pipeline data in FK-safe order. Returns deleted counts."""
    counts_before = get_counts(db)
    deleted = {}

    def delete_batched(model, name: str):
        count = db.query(model).count()
        deleted[name] = count
        if dry_run:
            logger.info("  %s: would delete %d", name, count)
            return count
        total = 0
        while True:
            batch = db.query(model).limit(BATCH_SIZE).all()
            if not batch:
                break
            ids = [r.id for r in batch]
            cnt = db.query(model).filter(model.id.in_(ids)).delete(synchronize_session="fetch")
            total += cnt
            db.flush()
            logger.info("  %s: deleted batch of %d", name, cnt)
        return total

    # 1. RecommendationResult
    logger.info("Deleting recommendation_results...")
    delete_batched(RecommendationResult, "recommendation_results")

    # 2. OutreachEmail
    logger.info("Deleting outreach_emails...")
    delete_batched(OutreachEmail, "outreach_emails")

    # 3. ProfessorResearchTag
    logger.info("Deleting professor_research_tags...")
    delete_batched(ProfessorResearchTag, "professor_research_tags")

    # 4. ProfessorProgram
    logger.info("Deleting professor_programs...")
    delete_batched(ProfessorProgram, "professor_programs")

    # 5. FundingOpportunity
    logger.info("Deleting funding_opportunities...")
    delete_batched(FundingOpportunity, "funding_opportunities")

    # 6. Professor
    logger.info("Deleting professors...")
    delete_batched(Professor, "professors")

    # 7. ProgramTag
    logger.info("Deleting program_tags...")
    delete_batched(ProgramTag, "program_tags")

    # 8. Essay - set target_program_id to NULL
    logger.info("Nullifying essay target_program_id...")
    n = db.query(Essay).filter(Essay.target_program_id.isnot(None)).count()
    deleted["essays_updated"] = n
    if not dry_run and n > 0:
        db.query(Essay).filter(Essay.target_program_id.isnot(None)).update(
            {Essay.target_program_id: None}, synchronize_session="fetch"
        )
        db.flush()

    # 9. Program
    logger.info("Deleting programs...")
    delete_batched(Program, "programs")

    # 10. ScrapeJob
    logger.info("Deleting scrape_jobs...")
    delete_batched(ScrapeJob, "scrape_jobs")

    # 11. Institution
    logger.info("Deleting institutions...")
    delete_batched(Institution, "institutions")

    if not dry_run:
        db.commit()

    return deleted


def clear_search_indexes(dry_run: bool = False) -> None:
    """Clear Meilisearch indexes for institutions, programs, funding."""
    if dry_run:
        logger.info("Would clear Meilisearch indexes (institutions, programs, funding)")
        return
    logger.info("Clearing Meilisearch indexes...")
    try:
        search_service.clear_all_indexes()
        logger.info("  Meilisearch indexes cleared")
    except Exception as exc:
        logger.warning("  Could not clear Meilisearch indexes: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset pipeline data: remove all schools, programs, faculty, funding"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without applying")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        counts = get_counts(db)
        total = sum(v for k, v in counts.items() if k != "essays_with_program")
        total += counts.get("essays_with_program", 0)

        logger.info("Current row counts:")
        for name, cnt in counts.items():
            logger.info("  %s: %d", name, cnt)

        if total == 0:
            logger.info("No pipeline data to delete. Exiting.")
            return

        if not args.dry_run and not args.yes:
            print("\nWARNING: This will PERMANENTLY delete all institutions, programs,")
            print("professors, funding, and scrape jobs. User accounts and sessions")
            print("will be preserved. Essay target_program_id will be nullified.")
            resp = input("\nType 'yes' to confirm: ")
            if resp.strip().lower() != "yes":
                logger.info("Aborted.")
                return

        logger.info("")
        if args.dry_run:
            logger.info("DRY RUN - no changes will be made")
            logger.info("")
        deleted = reset_pipeline_data(db, dry_run=args.dry_run)

        if not args.dry_run:
            clear_search_indexes(dry_run=False)

        logger.info("")
        logger.info("=" * 50)
        logger.info("RESET COMPLETE" + (" (dry run)" if args.dry_run else ""))
        logger.info("=" * 50)
        for name, cnt in deleted.items():
            logger.info("  %s: %d", name, cnt)
        logger.info("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    main()
    sys.exit(0)
