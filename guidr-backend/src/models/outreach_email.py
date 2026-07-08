"""OutreachEmail model for storing generated email drafts."""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class OutreachEmail(Base):
    """Outreach email model for storing email drafts."""

    __tablename__ = "outreach_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    professor_id = Column(UUID(as_uuid=True), ForeignKey("professors.id"), nullable=False, index=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=True, index=True)  # Optional link to program

    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    generation_context = Column(Text, nullable=True)  # Store context used for generation
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="outreach_emails")
    professor = relationship("Professor", back_populates="outreach_emails")
    program = relationship("Program", backref="outreach_emails")
