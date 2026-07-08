"""EssayVersion model for tracking essay revisions."""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class EssayVersion(Base):
    """Essay version model for tracking revisions."""

    __tablename__ = "essay_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    essay_id = Column(UUID(as_uuid=True), ForeignKey("essays.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    essay = relationship("Essay", back_populates="versions")
