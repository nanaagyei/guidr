"""Pydantic schemas for essays."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class EssayBase(BaseModel):
    """Base schema for essay."""
    title: str
    essay_type: Optional[str] = None
    target_program_id: Optional[UUID] = None


class EssayCreate(EssayBase):
    """Schema for creating essay."""
    content: str


class EssayUpdate(BaseModel):
    """Schema for updating essay."""
    title: Optional[str] = None
    content: Optional[str] = None


class EssayResponse(EssayBase):
    """Schema for essay response."""
    id: UUID
    user_id: UUID
    word_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EssayVersionResponse(BaseModel):
    """Schema for essay version response."""
    id: UUID
    version_number: int
    content: str
    word_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EssayReviewResponse(BaseModel):
    """Schema for essay review response."""
    id: UUID
    overall_score: Optional[Decimal] = None
    clarity_score: Optional[Decimal] = None
    structure_score: Optional[Decimal] = None
    content_score: Optional[Decimal] = None
    grammar_score: Optional[Decimal] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    suggestions: Optional[str] = None
    detailed_feedback: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

