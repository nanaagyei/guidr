"""Pydantic schemas for documents."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DocumentUploadUrlRequest(BaseModel):
    """Schema for requesting upload URL."""
    filename: str
    document_type: str  # 'transcript', 'resume', 'essay', 'other'


class DocumentUploadUrlResponse(BaseModel):
    """Schema for upload URL response."""
    upload_url: str
    document_id: UUID
    storage_key: str


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: UUID
    user_id: UUID
    document_type: str
    original_filename: str
    processing_status: str
    file_size_bytes: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    extracted_summary: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)

