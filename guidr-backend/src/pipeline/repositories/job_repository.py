"""Pipeline job repository: CRUD, fingerprint dedup, atomic claim/complete."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.pipeline_job import PipelineJob
from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint

logger = logging.getLogger(__name__)


class JobRepository:
    """Data access layer for pipeline_jobs table."""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        job_type: str,
        entity_kind: str,
        entity_id: Optional[str] = None,
        target_url: Optional[str] = None,
        priority: str = "high",
        schema_version: str = "v1",
        freshness_bucket: str = "default",
        source_document_id: Optional[str] = None,
        input_json: Optional[dict] = None,
        max_attempts: int = 5,
    ) -> PipelineJob:
        """Create a pipeline job with a computed fingerprint.

        Raises IntegrityError if a job with the same fingerprint already exists
        (dedup protection).
        """
        fingerprint, _ = compute_job_fingerprint(
            job_type=job_type,
            schema_version=schema_version,
            freshness_bucket=freshness_bucket,
            entity_kind=entity_kind,
            entity_id=entity_id,
            target_url=target_url,
        )

        job = PipelineJob(
            id=uuid.uuid4(),
            job_type=job_type,
            priority=priority,
            status="queued",
            entity_kind=entity_kind,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            source_document_id=uuid.UUID(source_document_id) if source_document_id else None,
            target_url=target_url,
            schema_version=schema_version,
            freshness_bucket=freshness_bucket,
            fingerprint=fingerprint,
            max_attempts=max_attempts,
            input_json=input_json or {},
        )
        self.db.add(job)
        self.db.flush()
        return job

    def find_recent_success(
        self,
        job_type: str,
        entity_kind: str,
        entity_id: Optional[str] = None,
        target_url: Optional[str] = None,
        schema_version: str = "v1",
        freshness_bucket: str = "default",
        window_hours: int = 24,
    ) -> Optional[PipelineJob]:
        """Find a recently succeeded job with matching fingerprint.

        Used to skip re-processing within the staleness window.
        """
        fingerprint, _ = compute_job_fingerprint(
            job_type=job_type,
            schema_version=schema_version,
            freshness_bucket=freshness_bucket,
            entity_kind=entity_kind,
            entity_id=entity_id,
            target_url=target_url,
        )
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        return (
            self.db.query(PipelineJob)
            .filter(
                PipelineJob.fingerprint == fingerprint,
                PipelineJob.status == "succeeded",
                PipelineJob.finished_at >= cutoff,
            )
            .first()
        )

    def find_in_progress(
        self,
        job_type: str,
        entity_kind: str,
        entity_id: Optional[str] = None,
        target_url: Optional[str] = None,
        schema_version: str = "v1",
        freshness_bucket: str = "default",
    ) -> Optional[PipelineJob]:
        """Find an in-progress (queued or running) job with matching fingerprint."""
        fingerprint, _ = compute_job_fingerprint(
            job_type=job_type,
            schema_version=schema_version,
            freshness_bucket=freshness_bucket,
            entity_kind=entity_kind,
            entity_id=entity_id,
            target_url=target_url,
        )
        return (
            self.db.query(PipelineJob)
            .filter(
                PipelineJob.fingerprint == fingerprint,
                PipelineJob.status.in_(["queued", "running"]),
            )
            .first()
        )

    def find_by_fingerprint(
        self,
        job_type: str,
        entity_kind: str,
        entity_id: Optional[str] = None,
        target_url: Optional[str] = None,
        schema_version: str = "v1",
        freshness_bucket: str = "default",
    ) -> Optional[PipelineJob]:
        """Find any job with matching fingerprint (any status)."""
        fingerprint, _ = compute_job_fingerprint(
            job_type=job_type,
            schema_version=schema_version,
            freshness_bucket=freshness_bucket,
            entity_kind=entity_kind,
            entity_id=entity_id,
            target_url=target_url,
        )
        return (
            self.db.query(PipelineJob)
            .filter(PipelineJob.fingerprint == fingerprint)
            .first()
        )

    def claim_job(self, job_id: str, run_by: str) -> Optional[PipelineJob]:
        """Atomically claim a queued job (UPDATE WHERE status='queued').

        Returns the job if claimed, None if already taken.
        """
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        rows = (
            self.db.query(PipelineJob)
            .filter(
                PipelineJob.id == job_uuid,
                PipelineJob.status == "queued",
            )
            .update(
                {
                    PipelineJob.status: "running",
                    PipelineJob.started_at: datetime.utcnow(),
                    PipelineJob.run_by: run_by,
                    PipelineJob.attempt: PipelineJob.attempt + 1,
                },
                synchronize_session="fetch",
            )
        )
        self.db.flush()
        if rows == 0:
            return None
        return self.db.query(PipelineJob).get(job_uuid)

    def complete_job(
        self,
        job_id: str,
        status: str = "succeeded",
        output_json: Optional[dict] = None,
        metrics_json: Optional[dict] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> PipelineJob:
        """Finalize a running job with outcome data."""
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        job = self.db.query(PipelineJob).get(job_uuid)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        job.status = status
        job.finished_at = datetime.utcnow()
        if output_json is not None:
            job.output_json = output_json
        if metrics_json is not None:
            job.metrics_json = metrics_json
        if error_code:
            job.error_code = error_code
        if error_message:
            job.error_message = error_message

        self.db.flush()
        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job. Returns True if cancelled."""
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        rows = (
            self.db.query(PipelineJob)
            .filter(
                PipelineJob.id == job_uuid,
                PipelineJob.status == "queued",
            )
            .update(
                {PipelineJob.status: "canceled", PipelineJob.finished_at: datetime.utcnow()},
                synchronize_session="fetch",
            )
        )
        self.db.flush()
        return rows > 0

    def requeue_job(self, job_id: str) -> Optional[PipelineJob]:
        """Requeue a failed job for retry."""
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        job = self.db.query(PipelineJob).get(job_uuid)
        if job is None or job.status != "failed":
            return None
        if job.attempt >= job.max_attempts:
            return None

        job.status = "queued"
        job.started_at = None
        job.finished_at = None
        job.error_code = None
        job.error_message = None
        self.db.flush()
        return job

    def get_job(self, job_id: str) -> Optional[PipelineJob]:
        """Get a job by ID."""
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        return self.db.query(PipelineJob).get(job_uuid)

    def list_jobs(
        self,
        entity_kind: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PipelineJob]:
        """Query jobs with optional filters."""
        q = self.db.query(PipelineJob)
        if entity_kind:
            q = q.filter(PipelineJob.entity_kind == entity_kind)
        if entity_id:
            q = q.filter(PipelineJob.entity_id == uuid.UUID(entity_id))
        if status:
            q = q.filter(PipelineJob.status == status)
        return q.order_by(PipelineJob.queued_at.desc()).offset(offset).limit(limit).all()
