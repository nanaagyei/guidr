#!/usr/bin/env python
"""
Load graduate schools from College Scorecard API.

Fetches all US schools offering graduate degrees (school.degrees_awarded.highest 3..4),
creates/updates Institution records, and indexes to Meilisearch.

Usage:
    python scripts/load_scorecard_schools.py
    python scripts/load_scorecard_schools.py --state CA
    python scripts/load_scorecard_schools.py --limit 10   # For testing

Requires COLLEGE_SCORECARD_API_KEY in .env.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import SessionLocal
from src.services.data_ingestion import DataIngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load graduate schools from College Scorecard API"
    )
    parser.add_argument("--state", type=str, default=None, help="Filter by state (e.g. CA, NY)")
    parser.add_argument("--limit", type=int, default=None, help="Max schools to load (for testing)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        result = service.load_graduate_schools_from_scorecard(
            state=args.state,
            limit=args.limit,
        )
        logger.info(
            "Load complete: inserted=%s updated=%s errors=%s",
            result.get("inserted", 0),
            result.get("updated", 0),
            result.get("errors", 0),
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
    sys.exit(0)
