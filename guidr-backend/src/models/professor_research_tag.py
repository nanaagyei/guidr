"""ProfessorResearchTag model for normalized research tags."""
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class ProfessorResearchTag(Base):
    """Professor research tag model for normalized tags."""
    
    __tablename__ = "professor_research_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professor_id = Column(UUID(as_uuid=True), ForeignKey("professors.id"), nullable=False, index=True)
    tag = Column(String, nullable=False, index=True)  # e.g., "machine learning", "NLP", "computer vision"
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    professor = relationship("Professor", back_populates="research_tags")

