"""PipelineJob model for advanced pipeline job tracking."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class PipelineJob(Base):
    """Maps to pipeline_jobs table (migration 014).

    Tracks enrichment jobs through the orchestrator pipeline with
    fingerprint-based deduplication and priority queuing.
    """

    __tablename__ = "pipeline_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="high")  # critical, high, bulk
    status = Column(String, nullable=False, default="queued")  # queued, running, succeeded, failed, canceled, skipped

    entity_kind = Column(String, nullable=True)  # school, program, professor, funding, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    source_document_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    target_url = Column(Text, nullable=True)

    schema_version = Column(String, nullable=False, default="v1")
    freshness_bucket = Column(String, nullable=False, default="default")
    fingerprint = Column(String, nullable=False, unique=True)
    dedup_group = Column(String, nullable=True)

    attempt = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)

    queued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    run_by = Column(String, nullable=True)

    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    input_json = Column(JSON, nullable=False, default=dict)
    output_json = Column(JSON, nullable=False, default=dict)
    metrics_json = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    extraction_runs = relationship("ExtractionRun", back_populates="job")
