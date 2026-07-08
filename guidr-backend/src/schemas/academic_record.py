"""Pydantic schemas for academic records."""
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional
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


class AcademicRecordUpdate(BaseModel):
    """Schema for updating academic record. All fields optional."""
    institution_name: Optional[str] = None
    country: Optional[str] = None
    degree_level: Optional[str] = None
    field_of_study: Optional[str] = None
    gpa_value: Optional[Decimal] = None
    gpa_scale: Optional[Decimal] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_current: Optional[bool] = None
    notes: Optional[str] = None


class AcademicRecordResponse(AcademicRecordBase):
    """Schema for academic record response."""
    id: UUID
    user_id: UUID
    normalized_gpa: Optional[Decimal] = None
    source: str
    completion: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
