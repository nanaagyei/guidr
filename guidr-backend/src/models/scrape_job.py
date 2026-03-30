"""ScrapeJob model for tracking scraping pipeline jobs."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class ScrapeJob(Base):
    """Track scraping jobs with status, type, and quality metrics."""

    __tablename__ = "scrape_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    job_type = Column(
        String,
        nullable=False,
        index=True,
    )  # 'overview', 'programs', 'faculty', 'funding', 'full_pipeline'
    status = Column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    pages_scraped = Column(Integer, default=0, nullable=False)
    items_extracted = Column(Integer, default=0, nullable=False)
    quality_score = Column(Integer, nullable=True)  # 0-100
    raw_data_path = Column(String, nullable=True)  # S3/MinIO path to raw data
    metadata_ = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
