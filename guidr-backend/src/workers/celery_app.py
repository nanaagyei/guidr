"""Celery application for Guidr background jobs."""
from celery import Celery

from src.config import settings

celery_app = Celery(
    "guidr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.workers.scraper_worker",
        "src.workers.document_processor",
        "src.pipeline.tasks.scrape_tasks",
        "src.pipeline.tasks.pipeline_tasks",
        "src.pipeline.tasks.orchestrator_tasks",
        "src.pipeline.tasks.maintenance_tasks",
        "src.pipeline.tasks.dossier_tasks",
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
        "pipeline.run_dossier": {"queue": "pipeline"},
        "pipeline.run_professor_match": {"queue": "pipeline"},
        "pipeline.critical.*": {"queue": "pipeline"},
        "pipeline.maintenance.*": {"queue": "default"},
        "pipeline.*": {"queue": "scraping"},
        "ingestion.*": {"queue": "default"},
        "search.*": {"queue": "default"},
        "scrape.*": {"queue": "scraping"},
        "document.*": {"queue": "processing"},
        "embeddings.*": {"queue": "processing"},
    },
    # Per-task rate limits, retry policy, and time limits.
    # soft_time_limit raises SoftTimeLimitExceeded (catchable);
    # time_limit is a hard SIGKILL (uncatchable).
    task_annotations={
        # Priority 0 = critical (user-facing, real-time)
        # Priority 3 = high (enrichment pipelines)
        # Priority 6 = normal (batch scraping, extraction)
        # Priority 9 = low (maintenance, cleanup)
        "pipeline.run_enrichment": {
            "rate_limit": "30/m",
            "max_retries": 5,
            "soft_time_limit": 300,
            "time_limit": 600,
            "priority": 3,
        },
        "pipeline.run_dossier": {
            "rate_limit": "10/m",
            "soft_time_limit": 300,
            "time_limit": 600,
            "priority": 0,  # user-facing — highest priority
        },
        "pipeline.run_professor_match": {
            "rate_limit": "10/m",
            "soft_time_limit": 240,
            "time_limit": 480,
            "priority": 0,  # user-facing — highest priority
        },
        "pipeline.extract_funding": {
            "soft_time_limit": 120,
            "time_limit": 180,
            "priority": 6,
        },
        "pipeline.extract_faculty": {
            "soft_time_limit": 120,
            "time_limit": 180,
            "priority": 6,
        },
        "pipeline.extract_programs": {
            "soft_time_limit": 120,
            "time_limit": 180,
            "priority": 6,
        },
        "pipeline.scrape_overview": {
            "soft_time_limit": 120,
            "time_limit": 180,
            "priority": 6,
        },
        "pipeline.maintenance.*": {
            "rate_limit": "5/m",
            "soft_time_limit": 60,
            "time_limit": 120,
            "priority": 9,  # lowest — background cleanup
        },
    },
    # Priority-within-queue ordering.
    # Redis does not natively support AMQP priorities, so Celery emulates them
    # by creating separate lists per priority level (0 = highest, 9 = lowest).
    # We use 4 steps to keep overhead low: 0 (critical), 3 (high), 6 (normal), 9 (low).
    broker_transport_options={
        "priority_steps": list(range(10)),
        "queue_order_strategy": "priority",
    },
    task_default_priority=6,  # normal priority for undecorated tasks
    # Beat schedule for recurring tasks
    beat_schedule=PIPELINE_BEAT_SCHEDULE,
)
