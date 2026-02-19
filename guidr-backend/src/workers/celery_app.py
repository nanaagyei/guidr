"""Celery application for Guidr background jobs."""
from celery import Celery

from src.config import settings

celery_app = Celery(
    "guidr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.workers.scraper_worker",
        "src.pipeline.tasks.scrape_tasks",
        "src.pipeline.tasks.pipeline_tasks",
        "src.pipeline.tasks.orchestrator_tasks",
        "src.pipeline.tasks.maintenance_tasks",
    ],
)

# Import beat schedule from pipeline
from src.pipeline.tasks.scheduled_tasks import PIPELINE_BEAT_SCHEDULE

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # Windows compatibility: use 'solo' pool instead of 'prefork'
    worker_pool="solo",
    # Task routing: separate queues for different workloads
    task_routes={
        "pipeline.run_enrichment": {"queue": "pipeline"},
        "pipeline.critical.*": {"queue": "pipeline"},
        "pipeline.maintenance.*": {"queue": "default"},
        "pipeline.*": {"queue": "scraping"},
        "ingestion.*": {"queue": "default"},
        "search.*": {"queue": "default"},
        "scrape.*": {"queue": "scraping"},
        "document.*": {"queue": "processing"},
        "embeddings.*": {"queue": "processing"},
    },
    # Retry policy for pipeline tasks
    task_annotations={
        "pipeline.run_enrichment": {
            "rate_limit": "30/m",
            "max_retries": 5,
        },
        "pipeline.maintenance.*": {
            "rate_limit": "5/m",
        },
    },
    # Beat schedule for recurring tasks
    beat_schedule=PIPELINE_BEAT_SCHEDULE,
)
