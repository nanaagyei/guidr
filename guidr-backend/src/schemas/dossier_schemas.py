"""Pydantic schemas for dossier endpoints."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils.sanitization import SAFE_TEXT_PATTERN as _SAFE_TEXT_PATTERN


class DossierRequest(BaseModel):
    """Request body for dossier endpoints."""
    force_refresh: bool = False


class ProfessorMatchRequest(BaseModel):
    """Request body for professor matching endpoint."""
    research_interests: list[str] = Field(default_factory=list)
    department: Optional[str] = Field(default=None, max_length=200)
    force_refresh: bool = False

    @field_validator("research_interests")
    @classmethod
    def validate_research_interests(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ValueError("Maximum 10 research interests allowed")
        cleaned = []
        for item in v:
            item = item.strip()
            if len(item) > 100:
                raise ValueError("Each research interest must be 100 characters or fewer")
            if item and not _SAFE_TEXT_PATTERN.match(item):
                raise ValueError(
                    "Research interest contains invalid characters. "
                    "Only alphanumeric, spaces, hyphens, commas, dots, slashes, "
                    "parentheses, ampersands, and apostrophes are allowed."
                )
            if item:
                cleaned.append(item)
        return cleaned

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()[:200]
            if v and not _SAFE_TEXT_PATTERN.match(v):
                raise ValueError(
                    "Department name contains invalid characters."
                )
        return v or None


class FundingDossierRequest(BaseModel):
    """Request body for funding dossier endpoint."""
    program_id: Optional[UUID] = None
    force_refresh: bool = False


class RecommendationRunRequest(BaseModel):
    """Request body for recommendation run endpoint."""
    trigger_source: Optional[str] = None
    force_refresh: bool = False


class DossierCacheValue(BaseModel):
    """Cached dossier data returned in responses."""
    value_json: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[Decimal] = None
    computed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    citations_json: list[dict] = Field(default_factory=list)
    evidence_map_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DossierResponseSchema(BaseModel):
    """Standard response for dossier endpoints."""
    status: str  # cache_hit, enqueued, dedup_in_progress, quota_exceeded
    job_id: Optional[str] = None
    cache: Optional[DossierCacheValue] = None
    message: Optional[str] = None
