"""ProgramTag model for tagging programs."""
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class ProgramTag(Base):
    """Program tag model for categorizing programs."""

    __tablename__ = "program_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False, index=True)
    tag_type = Column(String, nullable=False)  # 'research_area', 'keyword', 'strength'
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    program = relationship("Program", backref="tags")
