"""Pydantic schemas for school/institution pipeline data."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SchoolOverviewData(BaseModel):
    """Extracted overview data for an institution."""

    description: Optional[str] = None
    acceptance_rate: Optional[float] = Field(None, ge=0, le=100)
    enrollment_total: Optional[int] = Field(None, ge=0)
    grad_enrollment: Optional[int] = Field(None, ge=0)
    campus_setting: Optional[str] = None  # 'urban', 'suburban', 'rural'
    academic_calendar: Optional[str] = None  # 'semester', 'quarter', 'trimester'


class ScrapeJobCreate(BaseModel):
    """Schema for creating a new scrape job."""

    institution_id: Optional[str] = None
    job_type: str = Field(
        ...,
        pattern=r"^(overview|programs|faculty|funding|full_pipeline)$",
    )
