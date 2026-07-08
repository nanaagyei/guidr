"""Pydantic schemas for programs."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import date
from decimal import Decimal


class ProgramBase(BaseModel):
    """Base schema for program."""
    name: str
    degree_level: str
    delivery_mode: Optional[str] = None
    field_of_study: Optional[str] = None
    research_or_coursework: Optional[str] = None
    description: Optional[str] = None
    application_deadline_primary: Optional[date] = None
    application_deadline_secondary: Optional[date] = None
    tuition_estimate_per_year: Optional[Decimal] = None
    application_fee: Optional[Decimal] = None
    website_url: Optional[str] = None
    program_features: Optional[List[str]] = None


class ProgramResponse(ProgramBase):
    """Schema for program response."""
    id: UUID
    institution_id: UUID
    data_completeness_score: int
    data_source: str

    model_config = ConfigDict(from_attributes=True)


class ProgramDetailResponse(ProgramResponse):
    """Schema for detailed program response with institution info."""
    institution: Optional[dict] = None
    tags: Optional[List[dict]] = None
