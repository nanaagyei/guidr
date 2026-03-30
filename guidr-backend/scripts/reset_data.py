#!/usr/bin/env python
"""
Full data reset: clears all institution/program/faculty/funding data AND all
pipeline tables (pipeline_jobs, source_documents, raw_artifacts, extraction_runs,
entity_promotions, enrichment_cache).

User accounts, profiles, academic records, essays, and documents are preserved.
Meilisearch indexes are cleared. MinIO raw artifacts are NOT purged automatically.

Usage:
    python scripts/reset_data.py --dry-run   # Preview without changes
    python scripts/reset_data.py --yes       # Skip confirmation prompt
    python scripts/reset_data.py             # Interactive confirmation
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db import SessionLocal

# Pre-load all models so SQLAlchemy mapper is fully configured
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
from src.models.institution import Institution

# Pipeline models (migration 014+)
from src.models.entity_promotion import EntityPromotion
from src.models.extraction_run import ExtractionRun
from src.models.enrichment_cache import EnrichmentCache
from src.models.raw_artifact import RawArtifact
from src.models.source_document import SourceDocument
from src.models.pipeline_job import PipelineJob
from src.models.domain_health import DomainHealth

try:
    from src.models.scrape_job import ScrapeJob
    _HAS_SCRAPE_JOB = True
except ImportError:
    _HAS_SCRAPE_JOB = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count(db, model) -> int:
    return db.query(model).count()


def _delete_all(db, model, name: str, dry_run: bool) -> int:
    n = _count(db, model)
    if dry_run:
        logger.info("  [dry] %-40s %d rows", name, n)
        return n
    if n == 0:
        logger.info("  %-40s (empty)", name)
        return 0
    db.query(model).delete(synchronize_session=False)
    db.flush()
    logger.info("  %-40s deleted %d rows", name, n)
    return n


def _truncate(db, table: str, dry_run: bool, cascade: bool = False) -> None:
    """Fast TRUNCATE for tables that can't be easily enumerated via ORM."""
    suffix = " CASCADE" if cascade else ""
    if dry_run:
        logger.info("  [dry] TRUNCATE %s%s", table, suffix)
        return
    db.execute(text(f"TRUNCATE TABLE {table}{suffix}"))
    db.flush()
    logger.info("  TRUNCATE %s%s", table, suffix)


# ---------------------------------------------------------------------------
# Main reset
# ---------------------------------------------------------------------------

def reset_all(db, dry_run: bool) -> dict[str, int]:
    """Delete all pipeline + canonical data. Returns table → row counts deleted."""
    stats: dict[str, int] = {}

    logger.info("")
    logger.info("=== Step 1: Pipeline tables (migration 014+) ===")

    # entity_promotions depends on extraction_runs
    stats["entity_promotions"] = _delete_all(db, EntityPromotion, "entity_promotions", dry_run)
    # enrichment_cache
    stats["enrichment_cache"] = _delete_all(db, EnrichmentCache, "enrichment_cache", dry_run)
    # extraction_runs depends on raw_artifacts
    stats["extraction_runs"] = _delete_all(db, ExtractionRun, "extraction_runs", dry_run)
    # raw_artifacts depends on source_documents
    stats["raw_artifacts"] = _delete_all(db, RawArtifact, "raw_artifacts", dry_run)
    # source_documents
    stats["source_documents"] = _delete_all(db, SourceDocument, "source_documents", dry_run)
    # pipeline_jobs
    stats["pipeline_jobs"] = _delete_all(db, PipelineJob, "pipeline_jobs", dry_run)
    # domain_health (not entity-dependent — keep? clear for fresh start)
    stats["domain_health"] = _delete_all(db, DomainHealth, "domain_health", dry_run)

    logger.info("")
    logger.info("=== Step 2: Canonical entity tables ===")

    # Nullify essay target_program_id before deleting programs
    n_essays = db.query(Essay).filter(Essay.target_program_id.isnot(None)).count()
    stats["essays_nullified"] = n_essays
    if not dry_run and n_essays:
        db.query(Essay).filter(Essay.target_program_id.isnot(None)).update(
            {Essay.target_program_id: None}, synchronize_session=False
        )
        db.flush()
        logger.info("  %-40s nullified %d", "essay.target_program_id", n_essays)
    elif dry_run:
        logger.info("  [dry] %-40s %d essays would be nullified", "essay.target_program_id", n_essays)

    stats["recommendation_results"] = _delete_all(db, RecommendationResult, "recommendation_results", dry_run)
    stats["outreach_emails"] = _delete_all(db, OutreachEmail, "outreach_emails", dry_run)
    stats["professor_research_tags"] = _delete_all(db, ProfessorResearchTag, "professor_research_tags", dry_run)
    stats["professor_programs"] = _delete_all(db, ProfessorProgram, "professor_programs", dry_run)
    stats["funding_opportunities"] = _delete_all(db, FundingOpportunity, "funding_opportunities", dry_run)
    stats["professors"] = _delete_all(db, Professor, "professors", dry_run)
    stats["program_tags"] = _delete_all(db, ProgramTag, "program_tags", dry_run)
    stats["programs"] = _delete_all(db, Program, "programs", dry_run)

    if _HAS_SCRAPE_JOB:
        stats["scrape_jobs"] = _delete_all(db, ScrapeJob, "scrape_jobs", dry_run)

    stats["institutions"] = _delete_all(db, Institution, "institutions", dry_run)

    if not dry_run:
        db.commit()
        logger.info("")
        logger.info("All changes committed.")

    return stats


def clear_search_indexes(dry_run: bool) -> None:
    if dry_run:
        logger.info("[dry] Would clear Meilisearch indexes")
        return
    try:
        from src.services.search_service import search_service
        search_service.clear_all_indexes()
        logger.info("Meilisearch indexes cleared.")
    except Exception as exc:
        logger.warning("Could not clear Meilisearch indexes: %s", exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Full data reset for Guidr pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted, no changes")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Show current counts
        snapshot = {
            "institutions": _count(db, Institution),
            "programs": _count(db, Program),
            "professors": _count(db, Professor),
            "funding_opportunities": _count(db, FundingOpportunity),
            "pipeline_jobs": _count(db, PipelineJob),
            "source_documents": _count(db, SourceDocument),
            "raw_artifacts": _count(db, RawArtifact),
            "extraction_runs": _count(db, ExtractionRun),
            "enrichment_cache": _count(db, EnrichmentCache),
        }
        total = sum(snapshot.values())

        logger.info("Current row counts:")
        for tbl, cnt in snapshot.items():
            logger.info("  %-40s %d", tbl, cnt)

        if total == 0:
            logger.info("Nothing to delete. Exiting.")
            return

        if args.dry_run:
            logger.info("\nDRY RUN — no changes will be made\n")
        elif not args.yes:
            print("\nWARNING: This will PERMANENTLY delete all institutions, programs,")
            print("professors, funding, and all pipeline data. User accounts and")
            print("essay content are preserved.")
            resp = input("\nType 'yes' to confirm: ")
            if resp.strip().lower() != "yes":
                logger.info("Aborted.")
                return

        stats = reset_all(db, dry_run=args.dry_run)
        clear_search_indexes(dry_run=args.dry_run)

        logger.info("")
        logger.info("=" * 55)
        logger.info("RESET %s", "COMPLETE (dry run)" if args.dry_run else "COMPLETE")
        logger.info("=" * 55)
        for tbl, cnt in stats.items():
            if cnt:
                logger.info("  %-40s %d", tbl, cnt)
        logger.info("=" * 55)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. python scripts/load_scorecard_schools.py   # re-seed institutions")
        logger.info("  2. POST /ingestion/pipeline/bulk-enrich        # queue enrichment jobs")

    finally:
        db.close()


if __name__ == "__main__":
    main()
    sys.exit(0)
