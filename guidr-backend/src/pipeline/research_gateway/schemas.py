"""Request/response schemas for Research Gateway."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EntityContext(BaseModel):
    """Entity being researched."""
    entity_type: str  # SCHOOL, PROGRAM, PROFESSOR, DEPARTMENT
    entity_id: Optional[str] = None
    name: Optional[str] = None
    website_hint: Optional[str] = None
    program_name: Optional[str] = None
    department: Optional[str] = None


class Constraints(BaseModel):
    """Search constraints."""
    domains_allowlist: list[str] = Field(default_factory=list)
    domains_blocklist: list[str] = Field(default_factory=list)
    max_results: int = 10
    freshness_hours: int = 168
    language: str = "en"


class Budget(BaseModel):
    """Cost and token limits."""
    max_tokens: int = 12000
    max_cost_usd: float = 0.25
    priority: str = "HIGH"  # CRITICAL, HIGH, BULK


class CacheConfig(BaseModel):
    """Cache behavior."""
    dedupe_key: Optional[str] = None
    use_cache: bool = True
    max_age_hours: int = 168


class Trace(BaseModel):
    """Request tracing."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    source: Optional[str] = None  # scraper, ui, scheduler


class ResearchRequest(BaseModel):
    """Request to run a research job."""
    job_type: str  # URL_DISCOVERY, CHANGE_CHECK, REPAIR_EXTRACTION, SYNTHESIS_SUMMARY,
    #               DOSSIER_EXTRACTION, RECOMMENDATION_RUN, PROFESSOR_SYNTHESIS, FUNDING_DOSSIER
    entity: EntityContext
    category: str  # SCHOOL_OVERVIEW, PROGRAM_REQUIREMENTS, etc.
    prompt_override: Optional[str] = None  # Pre-rendered prompt for dossier jobs
    constraints: Constraints = Field(default_factory=Constraints)
    budget: Budget = Field(default_factory=Budget)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    trace: Trace = Field(default_factory=Trace)


class URLDiscoveryResult(BaseModel):
    """Single URL result from discovery."""
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    source: str = "unknown"
    retrieved_at: Optional[str] = None


class Citation(BaseModel):
    """Citation for a source."""
    url: str
    publisher: Optional[str] = None
    accessed_at: Optional[str] = None


class Metrics(BaseModel):
    """Job metrics."""
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    cache_hit: bool = False


class ResearchResponse(BaseModel):
    """Response from research job."""
    status: str  # SUCCESS, PARTIAL, FAILED
    job_type: str
    category: str
    entity: dict[str, Any] = Field(default_factory=dict)
    results: list[URLDiscoveryResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    errors: list[str] = Field(default_factory=list)


# --- Dossier-specific schemas ---

class DossierCitation(BaseModel):
    """Citation with structured metadata for dossier results."""
    id: str  # e.g. "c1", "c2"
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    publisher: Optional[str] = None


class DossierResponse(BaseModel):
    """Response from a dossier extraction job."""
    status: str  # SUCCESS, PARTIAL, FAILED
    final_json: dict[str, Any] = Field(default_factory=dict)
    report_markdown: Optional[str] = None
    citations: list[DossierCitation] = Field(default_factory=list)
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)  # field -> [citation_ids]
    metrics: Metrics = Field(default_factory=Metrics)
    errors: list[str] = Field(default_factory=list)


# Job type constants
DOSSIER_JOB_TYPES = frozenset({
    "DOSSIER_EXTRACTION",
    "RECOMMENDATION_RUN",
    "PROFESSOR_SYNTHESIS",
    "FUNDING_DOSSIER",
})
