"""RecommendationResult model for storing individual program recommendations."""
from sqlalchemy import Column, String, Integer, Numeric, Text, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base
import enum


class RecommendationTier(str, enum.Enum):
    DREAM = "dream"
    REACH = "reach"
    TARGET = "target"
    SAFETY = "safety"


class RecommendationResult(Base):
    """Recommendation result model for storing program recommendations."""

    __tablename__ = "recommendation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_session_id = Column(UUID(as_uuid=True), ForeignKey("recommendation_sessions.id"), nullable=False, index=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True)

    rank = Column(Integer, nullable=False)  # Ranking position (1 = best match)
    score = Column(Numeric(5, 2), nullable=False)  # Score 0-100
    tier = Column(String(20), nullable=False)  # dream, reach, target, safety

    explanation = Column(Text, nullable=True)  # Text explanation of why this program fits
    reason_features = Column(JSON, nullable=True)  # Array of feature matches used for explanation
    citations_json = Column(JSON, nullable=False, default=list)
    evidence_map_json = Column(JSON, nullable=False, default=dict)

    # AI-generated metadata (populated by dossier pipeline when program_id is NULL)
    school_name = Column(String, nullable=True)
    program_name = Column(String, nullable=True)
    institution_city = Column(String, nullable=True)
    institution_country = Column(String, nullable=True)
    funding_summary = Column(Text, nullable=True)
    deadline = Column(String, nullable=True)
    website_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("RecommendationSession", back_populates="results")
    program = relationship("Program", backref="recommendation_results")
