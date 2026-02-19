"""Pydantic schemas for academic records."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from decimal import Decimal


class AcademicRecordBase(BaseModel):
    """Base schema for academic record."""
    institution_name: str
    country: str
    degree_level: str  # 'bachelors', 'masters', 'phd', 'other'
    field_of_study: Optional[str] = None
    gpa_value: Optional[Decimal] = None
    gpa_scale: Optional[Decimal] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: bool = False
    notes: Optional[str] = None


class AcademicRecordCreate(AcademicRecordBase):
    """Schema for creating academic record."""
    pass


class AcademicRecordResponse(AcademicRecordBase):
    """Schema for academic record response."""
    id: UUID
    user_id: UUID
    normalized_gpa: Optional[Decimal] = None
    source: str
    
    model_config = ConfigDict(from_attributes=True)

