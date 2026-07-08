"""DocumentProcessingLog model for tracking processing jobs."""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class DocumentProcessingLog(Base):
    """Document processing log model for tracking worker jobs."""

    __tablename__ = "document_processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    job_type = Column(String, nullable=False)  # 'ocr', 'transcript_extraction', 'resume_extraction', etc.
    status = Column(String, default="queued", nullable=False)  # 'queued', 'running', 'succeeded', 'failed'
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    worker_id = Column(String, nullable=True)

    # Relationship
    document = relationship("Document", backref="processing_logs")
