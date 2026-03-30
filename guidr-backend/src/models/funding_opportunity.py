"""FundingOpportunity model for scholarships, fellowships, and assistantships."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class FundingOpportunity(Base):
    """Funding opportunities linked to institutions."""

    __tablename__ = "funding_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        UUID(as_uuid=True),
        ForeignKey("programs.id"),
        nullable=True,
        index=True,
    )
    name = Column(String, nullable=False)
    funding_type = Column(
        String, nullable=False, index=True
    )  # 'fellowship', 'assistantship', 'scholarship', 'grant', 'waiver'
    amount_min = Column(Numeric(12, 2), nullable=True)
    amount_max = Column(Numeric(12, 2), nullable=True)
    amount_period = Column(
        String, nullable=True
    )  # 'annual', 'semester', 'one_time', 'monthly'
    deadline = Column(Date, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)
    is_need_based = Column(Boolean, nullable=True)
    is_merit_based = Column(Boolean, nullable=True)
    covers_tuition = Column(Boolean, nullable=True)
    covers_stipend = Column(Boolean, nullable=True)
    source_url = Column(String, nullable=True)
    data_source = Column(String, default="web_scrape", nullable=False)

    # Enrichment tracking (set by promote_write node)
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)
    last_enrichment_confidence = Column(Numeric(4, 3), nullable=True)
    data_version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    institution = relationship("Institution", backref="funding_opportunities")
    program = relationship("Program", backref="funding_opportunities")
