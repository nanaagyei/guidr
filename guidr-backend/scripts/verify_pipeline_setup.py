#!/usr/bin/env python
"""Verify pipeline setup: database, MinIO, Redis, API keys."""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    issues = []
    print("Verifying pipeline setup...\n")

    # Database
    try:
        from src.db import SessionLocal
        from src.models.institution import Institution

        db = SessionLocal()
        count = db.query(Institution).count()
        db.close()
        print(f"  [OK] PostgreSQL: connected ({count} institutions)")
    except Exception as e:
        issues.append(f"PostgreSQL: {e}")
        print(f"  [FAIL] PostgreSQL: {e}")

    # Redis
    try:
        import redis
        from src.config import settings

        r = redis.from_url(settings.redis_url)
        r.ping()
        print("  [OK] Redis: connected")
    except Exception as e:
        issues.append(f"Redis: {e}")
        print(f"  [FAIL] Redis: {e}")

    # MinIO
    try:
        from src.pipeline.clients.storage_client import DataLakeStorageClient

        client = DataLakeStorageClient()
        if client._get_client():
            print("  [OK] MinIO: connected")
        else:
            print("  [WARN] MinIO: not configured or unavailable (pipeline will still run)")
    except Exception as e:
        print(f"  [WARN] MinIO: {e}")

    # API keys
    from src.config import settings

    if settings.college_scorecard_api_key:
        print("  [OK] COLLEGE_SCORECARD_API_KEY: set")
    else:
        print("  [WARN] COLLEGE_SCORECARD_API_KEY: not set (Scorecard load disabled)")

    if settings.firecrawl_api_key:
        print("  [OK] FIRECRAWL_API_KEY: set")
    else:
        print("  [WARN] FIRECRAWL_API_KEY: not set (scraping disabled)")

    # Staging schema
    try:
        from sqlalchemy import text
        from src.db import SessionLocal

        db = SessionLocal()
        row = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'staging'")).fetchone()
        db.close()
        if row:
            print("  [OK] Staging schema: exists")
        else:
            print("  [WARN] Staging schema: not found (run: alembic upgrade head)")
    except Exception as e:
        print(f"  [WARN] Staging schema: {e}")

    print()
    if issues:
        print("Fix the issues above, then run: alembic upgrade head")
        sys.exit(1)
    print("Pipeline setup verified successfully.")


if __name__ == "__main__":
    main()
