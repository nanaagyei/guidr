"""Pydantic schemas for institutions."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InstitutionResponse(BaseModel):
    """Schema for institution response."""

    id: UUID
    name: str
    short_name: Optional[str] = None
    country: str
    state_or_province: Optional[str] = None
    city: Optional[str] = None
    website_url: Optional[str] = None
    institution_type: Optional[str] = None
    public_private: Optional[str] = None
    overall_rank: Optional[int] = None
    ipeds_unit_id: Optional[str] = None
    average_cost: Optional[Decimal] = None
    in_state_tuition: Optional[Decimal] = None
    out_of_state_tuition: Optional[Decimal] = None
    graduation_rate: Optional[Decimal] = None
    median_earnings: Optional[Decimal] = None
    data_completeness_score: int
    last_enriched_at: Optional[datetime] = None
    last_enrichment_confidence: Optional[Decimal] = None
    data_version: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
