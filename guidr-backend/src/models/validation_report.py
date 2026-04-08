"""ValidationReport model for structured validation results."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class ValidationReport(Base):
    """Maps to validation_reports table (migration 019).

    Stores field-level validation results from the DataValidator, including
    pass/fail status, per-field outcomes, warnings, and errors. Linked to
    the extraction run that produced the data being validated.
    """

    __tablename__ = "validation_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    pipeline_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entity_kind = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    validator_name = Column(String, nullable=False)
    validator_version = Column(String, nullable=False, default="v1")
    schema_version = Column(String, nullable=False, default="v1")

    passed = Column(Boolean, nullable=False)
    overall_score = Column(Numeric(4, 3), nullable=True)

    field_results_json = Column(JSONB, nullable=False, default=list)
    warnings_json = Column(JSONB, nullable=False, default=list)
    errors_json = Column(JSONB, nullable=False, default=list)
    metadata_json = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    extraction_run = relationship("ExtractionRun", back_populates="validation_reports")
    pipeline_job = relationship("PipelineJob", back_populates="validation_reports")
