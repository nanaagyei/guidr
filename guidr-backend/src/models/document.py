"""Document model for uploaded files."""
from sqlalchemy import Column, String, Integer, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class Document(Base):
    """Document model for uploaded files."""
    
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)  # 'transcript', 'resume', 'essay', 'other'
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)  # Path in R2/S3
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=True)
    processing_status = Column(String, default="pending", nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    processing_error_message = Column(String, nullable=True)
    is_scanned = Column(Boolean, default=False, nullable=False)
    ocr_confidence = Column(Numeric(5, 2), nullable=True)
    extracted_summary = Column(JSON, nullable=True)  # Structured extracted data
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", backref="documents")

