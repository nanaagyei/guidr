"""Pydantic schemas for program extraction and validation."""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class ProgramExtractionData(BaseModel):
    """Extracted program data from web scraping."""

    name: str = Field(..., min_length=2, max_length=500)
    degree_level: Optional[str] = None  # 'masters', 'phd', 'professional'
    field_of_study: Optional[str] = None
    description: Optional[str] = None
    delivery_mode: Optional[str] = None  # 'in_person', 'online', 'hybrid'
    research_or_coursework: Optional[str] = None  # 'research', 'coursework', 'mixed'
    duration_months: Optional[int] = Field(None, ge=1, le=120)
    gre_required: Optional[bool] = None
    minimum_gpa: Optional[float] = Field(None, ge=0, le=4.0)
    application_deadline_primary: Optional[date] = None
    tuition_estimate_per_year: Optional[float] = Field(None, ge=0)
    application_fee: Optional[float] = Field(None, ge=0)
    website_url: Optional[str] = None
    program_features: Optional[List[str]] = None
