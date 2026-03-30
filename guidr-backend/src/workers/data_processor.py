"""Celery tasks for processing scraped raw data."""
from __future__ import annotations

from pathlib import Path

from src.workers.celery_app import celery_app


@celery_app.task(name="process.raw_data")
def process_raw_html(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)
    # Placeholder: a real implementation would feed this into LLM extraction.
    return {"path": path, "size": file_path.stat().st_size}

