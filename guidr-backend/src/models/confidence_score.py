"""ConfidenceScore model for historical confidence tracking."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class ConfidenceScore(Base):
    """Maps to confidence_scores table (migration 019).

    Records the composite confidence score and its component sub-scores
    (source, extraction, validation, staleness) for each extraction run.
    Enables historical tracking of confidence trends per entity.
    """

    __tablename__ = "confidence_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
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

    scorer_version = Column(String, nullable=False, default="v1")
    overall_confidence = Column(Numeric(4, 3), nullable=False)

    source_score = Column(Numeric(4, 3), nullable=True)
    extraction_score = Column(Numeric(4, 3), nullable=True)
    validation_score = Column(Numeric(4, 3), nullable=True)
    staleness_score = Column(Numeric(4, 3), nullable=True)

    weights_json = Column(JSONB, nullable=False, default=dict)
    details_json = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    extraction_run = relationship("ExtractionRun", back_populates="confidence_scores")
    pipeline_job = relationship("PipelineJob", back_populates="confidence_scores")
