"""Pydantic schemas for funding opportunity validation."""
from datetime import date
from enum import Enum
from typing import List, Optional

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


class ExternalFundingOpportunity(BaseModel):
    """An external fellowship, scholarship, or grant (outside the institution)."""

    name: str = Field(..., min_length=2, max_length=500)
    funder: Optional[str] = None           # e.g., "National Science Foundation"
    type: Optional[str] = None             # fellowship|scholarship|grant
    description: Optional[str] = None
    amount_min: Optional[float] = Field(None, ge=0)
    amount_max: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = "USD"
    deadline: Optional[str] = None        # Date string or description
    url: Optional[str] = None             # Official application URL
    eligibility_note: Optional[str] = None
    is_renewable: Optional[bool] = None
    duration_years: Optional[int] = None
    citations: Optional[List[str]] = None  # Citation marker list e.g. ["c8", "c9"]


class FundingDossierResult(BaseModel):
    """Full funding dossier returned by the agentic pipeline."""

    funding_opportunities: List[FundingOpportunityCreate] = Field(default_factory=list)
    external_opportunities: List[ExternalFundingOpportunity] = Field(default_factory=list)
    summary: Optional[str] = None
