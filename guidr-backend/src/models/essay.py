"""Essay model for user essays."""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class Essay(Base):
    """Essay model for user essays."""
    
    __tablename__ = "essays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    essay_type = Column(String, nullable=True)  # 'statement_of_purpose', 'personal_statement', etc.
    target_program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=True)
    word_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="essays")
    versions = relationship("EssayVersion", back_populates="essay", order_by="EssayVersion.version_number")
    reviews = relationship("EssayReview", back_populates="essay")

