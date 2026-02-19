"""Pydantic schemas for the enrichment API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EntityKind(str, Enum):
    school = "school"
    program = "program"
    professor = "professor"
    funding = "funding"


class EnrichmentPriority(str, Enum):
    critical = "critical"
    high = "high"
    bulk = "bulk"


class EnrichmentStatus(str, Enum):
    cache_hit = "cache_hit"
    enqueued = "enqueued"
    dedup_in_progress = "dedup_in_progress"
    quota_exceeded = "quota_exceeded"


# --- Requests ---


class EnrichRequest(BaseModel):
    entity_kind: EntityKind
    entity_id: str
    priority: EnrichmentPriority = EnrichmentPriority.high
    force_refresh: bool = False


class ShortlistEnrichRequest(BaseModel):
    items: list[EnrichRequest] = Field(..., max_length=20)


# --- Responses ---


class CachedValue(BaseModel):
    value: dict[str, Any]
    confidence: Optional[float] = None
    computed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class JobInfo(BaseModel):
    job_id: str
    status: str
    priority: str


class EnrichResponse(BaseModel):
    status: EnrichmentStatus
    cache: Optional[CachedValue] = None
    job: Optional[JobInfo] = None
    message: Optional[str] = None


class CacheStatusResponse(BaseModel):
    has_cache: bool
    confidence: Optional[float] = None
    computed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_stale: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[list[str]] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
