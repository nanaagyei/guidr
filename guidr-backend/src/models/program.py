"""Program model for graduate programs."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class Program(Base):
    """Program model for graduate programs."""

    __tablename__ = "programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    degree_level = Column(String, nullable=False, index=True)  # 'masters', 'phd'
    delivery_mode = Column(String, nullable=True)  # 'in_person', 'online', 'hybrid'
    field_of_study = Column(String, nullable=True, index=True)
    research_or_coursework = Column(String, nullable=True)  # 'research', 'coursework', 'mixed'
    description = Column(String, nullable=True)
    application_deadline_primary = Column(Date, nullable=True)
    application_deadline_secondary = Column(Date, nullable=True)
    tuition_estimate_per_year = Column(Numeric(10, 2), nullable=True)
    application_fee = Column(Numeric(10, 2), nullable=True)
    website_url = Column(String, nullable=True)
    program_features = Column(JSON, nullable=True)  # Array of feature strings
    data_completeness_score = Column(Integer, default=0, nullable=False)  # 0-100
    data_source = Column(String, default="manual", nullable=False)
    embedding = Column(Vector(384), nullable=True)

    # Pipeline enrichment fields
    duration_months = Column(Integer, nullable=True)
    gre_required = Column(Boolean, nullable=True)
    minimum_gpa = Column(Numeric(3, 2), nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    institution = relationship("Institution", back_populates="programs")
