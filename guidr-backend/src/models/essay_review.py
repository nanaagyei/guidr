"""EssayReview model for LLM-generated feedback."""
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class EssayReview(Base):
    """Essay review model for storing LLM feedback."""
    
    __tablename__ = "essay_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    essay_id = Column(UUID(as_uuid=True), ForeignKey("essays.id"), nullable=False, index=True)
    essay_version_id = Column(UUID(as_uuid=True), ForeignKey("essay_versions.id"), nullable=False)
    
    # Scores (0-10)
    overall_score = Column(Numeric(3, 1), nullable=True)
    clarity_score = Column(Numeric(3, 1), nullable=True)
    structure_score = Column(Numeric(3, 1), nullable=True)
    content_score = Column(Numeric(3, 1), nullable=True)
    grammar_score = Column(Numeric(3, 1), nullable=True)
    
    # Feedback text
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    detailed_feedback = Column(Text, nullable=True)
    
    # Metadata
    review_metadata = Column(JSON, nullable=True)  # Additional structured feedback
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    essay = relationship("Essay", back_populates="reviews")

