"""Reindex Meilisearch indexes from PostgreSQL data."""
from src.db import SessionLocal
from src.services.data_ingestion import DataIngestionService


def main():
    db = SessionLocal()
    try:
        service = DataIngestionService(db)
        result = service.reindex_search()
        print("Reindexed:", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
