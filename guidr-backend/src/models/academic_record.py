"""AcademicRecord model for user's academic history."""
from sqlalchemy import Column, String, Integer, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class AcademicRecord(Base):
    """Academic record model for storing user's academic history."""
    
    __tablename__ = "academic_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    institution_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    degree_level = Column(String, nullable=False)  # 'bachelors', 'masters', 'phd', 'other'
    field_of_study = Column(String, nullable=True)
    gpa_value = Column(Numeric(3, 2), nullable=True)
    gpa_scale = Column(Numeric(4, 2), nullable=True)  # e.g., 4.0, 10.0, 100.0
    normalized_gpa = Column(Numeric(3, 2), nullable=True)  # Converted to 4.0 scale
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    source = Column(String, default="manual", nullable=False)  # 'manual' or 'transcript_extraction'
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("User", backref="academic_records")

