"""ExtractionRun model for LLM extraction results."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class ExtractionRun(Base):
    """Maps to extraction_runs table (migration 014).

    Records each LLM or rule-based extraction attempt against a raw artifact,
    including the extracted JSON, confidence, validation state, and cost metrics.
    """

    __tablename__ = "extraction_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    raw_artifact_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    entity_kind = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    extractor_name = Column(String, nullable=False)
    model_name = Column(String, nullable=True)
    prompt_version = Column(String, nullable=False, default="v1")
    schema_version = Column(String, nullable=False, default="v1")

    extracted_json = Column(JSON, nullable=False)
    citations_json = Column(JSON, nullable=False, default=list)
    confidence = Column(Numeric(4, 3), nullable=True)

    status = Column(String, nullable=False, default="draft")  # draft, validated, promoted, rejected
    validation_json = Column(JSON, nullable=False, default=dict)
    token_usage_json = Column(JSON, nullable=False, default=dict)
    latency_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    job = relationship("PipelineJob", back_populates="extraction_runs")
    raw_artifact = relationship("RawArtifact", back_populates="extraction_runs")
    promotions = relationship("EntityPromotion", back_populates="extraction_run")
