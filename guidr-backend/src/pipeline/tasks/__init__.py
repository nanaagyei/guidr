"""Celery tasks for the scraping pipeline."""
from src.pipeline.tasks.scrape_tasks import (  # noqa: F401
    extract_funding_for_institution,
    extract_faculty_for_institution,
    extract_programs_for_institution,
    scrape_overview_for_institution,
)
from src.pipeline.tasks.pipeline_tasks import (  # noqa: F401
    run_full_pipeline,
    batch_scrape_institutions,
    refresh_stale_institutions,
)
