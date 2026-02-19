"""Pydantic schemas for funding opportunity validation."""
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FundingType(str, Enum):
    FELLOWSHIP = "fellowship"
    ASSISTANTSHIP = "assistantship"
    SCHOLARSHIP = "scholarship"
    GRANT = "grant"
    WAIVER = "waiver"


class AmountPeriod(str, Enum):
    ANNUAL = "annual"
    SEMESTER = "semester"
    ONE_TIME = "one_time"
    MONTHLY = "monthly"


class FundingOpportunityCreate(BaseModel):
    """Validated funding opportunity data ready for persistence."""

    name: str = Field(..., min_length=2, max_length=500)
    funding_type: FundingType
    amount_min: Optional[float] = Field(None, ge=0)
    amount_max: Optional[float] = Field(None, ge=0)
    amount_period: Optional[AmountPeriod] = None
    deadline: Optional[date] = None
    eligibility_criteria: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    is_need_based: Optional[bool] = None
    is_merit_based: Optional[bool] = None
    covers_tuition: Optional[bool] = None
    covers_stipend: Optional[bool] = None
    source_url: Optional[str] = None
