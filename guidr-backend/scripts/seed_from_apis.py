"""Seed data from IPEDS + College Scorecard APIs."""
import argparse
from contextlib import contextmanager

from src.db import SessionLocal
from src.services.data_ingestion import DataIngestionService


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run(year: str, limit: int | None):
    with session_scope() as db:
        service = DataIngestionService(db)
        ipeds_result = service.ingest_ipeds(year=year, limit=limit)
        scorecard_result = service.enrich_with_scorecard()
        print("IPEDS:", ipeds_result)
        print("Scorecard:", scorecard_result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database using IPEDS + College Scorecard APIs.")
    parser.add_argument("--year", default="2022", help="IPEDS data year, e.g. 2022")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for test runs")
    args = parser.parse_args()
    run(year=args.year, limit=args.limit)

