"""Institution model for universities and schools."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class Institution(Base):
    """Institution model for universities and schools."""

    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    short_name = Column(String, nullable=True)
    country = Column(String, nullable=False, index=True)
    state_or_province = Column(String, nullable=True)
    city = Column(String, nullable=True, index=True)
    website_url = Column(String, nullable=True)
    institution_type = Column(String, nullable=True)  # 'university', 'college', etc.
    public_private = Column(String, nullable=True)  # 'public', 'private'
    overall_rank = Column(Integer, nullable=True)

    # World rankings from different sources
    qs_world_rank = Column(Integer, nullable=True, index=True)
    the_world_rank = Column(Integer, nullable=True, index=True)  # Times Higher Ed
    arwu_rank = Column(Integer, nullable=True)  # Shanghai Ranking
    usnews_rank = Column(Integer, nullable=True)  # US News

    ipeds_unit_id = Column(String, nullable=True, unique=True, index=True)
    scorecard_school_id = Column(String, nullable=True, unique=True, index=True)
    average_cost = Column(Numeric(12, 2), nullable=True)
    in_state_tuition = Column(Numeric(12, 2), nullable=True)
    out_of_state_tuition = Column(Numeric(12, 2), nullable=True)
    graduation_rate = Column(Numeric(5, 2), nullable=True)
    median_earnings = Column(Numeric(12, 2), nullable=True)
    data_source = Column(String, nullable=False, default="manual")
    data_completeness_score = Column(Integer, default=0, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    # Enrichment fields (populated by pipeline scraping)
    description = Column(Text, nullable=True)
    acceptance_rate = Column(Numeric(5, 2), nullable=True)
    enrollment_total = Column(Integer, nullable=True)
    grad_enrollment = Column(Integer, nullable=True)
    campus_setting = Column(String, nullable=True)  # 'urban', 'suburban', 'rural'
    academic_calendar = Column(String, nullable=True)  # 'semester', 'quarter', 'trimester'

    # Pipeline tracking
    last_scraped_at = Column(DateTime, nullable=True)
    scrape_status = Column(String, nullable=True)  # 'pending', 'scraping', 'completed', 'failed'

    # Enrichment tracking (set by promote_write node)
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)
    last_enrichment_confidence = Column(Numeric(4, 3), nullable=True)
    data_version = Column(Integer, nullable=False, default=1)

    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    programs = relationship("Program", back_populates="institution")
