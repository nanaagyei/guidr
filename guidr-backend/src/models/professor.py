"""Professor model for faculty members and researchers."""
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Integer, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class Professor(Base):
    """Professor model for storing faculty information."""

    __tablename__ = "professors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False, index=True)

    full_name = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)  # "Assistant Professor", "Associate Professor", etc.
    email = Column(String, nullable=True)
    personal_page_url = Column(String, nullable=True)
    scholar_profile_url = Column(String, nullable=True)  # Google Scholar or similar
    openalex_id = Column(String(64), nullable=True, index=True)
    semantic_scholar_id = Column(String(64), nullable=True, index=True)
    orcid_id = Column(String(32), nullable=True, index=True)
    research_summary = Column(String, nullable=True)  # Free-form description
    interests_tags = Column(JSON, nullable=True)  # Array of high-level research topics
    professor_embedding = Column(JSON, nullable=True)  # Vector for semantic matching (future)
    is_accepting_students = Column(Boolean, nullable=True)  # Heuristic (can be inferred later)
    last_scraped_at = Column(DateTime, nullable=True)

    # Enrichment tracking (set by promote_write node)
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)
    last_enrichment_confidence = Column(Numeric(4, 3), nullable=True)
    data_version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    institution = relationship("Institution", backref="professors")
    research_tags = relationship("ProfessorResearchTag", back_populates="professor", cascade="all, delete-orphan")
    outreach_emails = relationship("OutreachEmail", back_populates="professor")
