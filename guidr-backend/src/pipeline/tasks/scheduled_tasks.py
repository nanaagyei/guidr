"""Celery Beat schedule definitions for recurring pipeline tasks."""
from celery.schedules import crontab


# Beat schedule to be merged into celery_app.conf.beat_schedule
PIPELINE_BEAT_SCHEDULE = {
    # Re-scrape institutions that haven't been scraped in 30 days
    "refresh-stale-institutions": {
        "task": "pipeline.refresh_stale",
        "schedule": crontab(hour=3, minute=0, day_of_week="monday"),
        "options": {"queue": "scraping"},
    },
    # Enrich institutions from College Scorecard weekly
    "weekly-scorecard-enrichment": {
        "task": "ingestion.scorecard",
        "schedule": crontab(hour=4, minute=0, day_of_week="wednesday"),
        "options": {"queue": "default"},
    },
    # Reindex search weekly
    "weekly-search-reindex": {
        "task": "search.reindex",
        "schedule": crontab(hour=5, minute=0, day_of_week="sunday"),
        "options": {"queue": "default"},
    },
    # --- Maintenance tasks ---
    # Purge expired enrichment cache entries daily at 2 AM
    "daily-purge-expired-cache": {
        "task": "pipeline.maintenance.purge_expired_cache",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
    # Reset stale domain blocks weekly on Saturday at 3 AM
    "weekly-reset-domain-health": {
        "task": "pipeline.maintenance.reset_domain_health",
        "schedule": crontab(hour=3, minute=0, day_of_week="saturday"),
        "options": {"queue": "default"},
    },
    # Clean up old pipeline jobs (>90 days) monthly on 1st at 4 AM
    "monthly-cleanup-old-jobs": {
        "task": "pipeline.maintenance.cleanup_old_jobs",
        "schedule": crontab(hour=4, minute=0, day_of_month="1"),
        "options": {"queue": "default"},
    },
}
