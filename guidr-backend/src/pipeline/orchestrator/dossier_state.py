"""Typed state for dossier graph."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class DossierState(TypedDict, total=False):
    """State passed between dossier graph nodes."""

    # Job identification
    job_id: str
    pipeline_job_id: Optional[str]
    job_type: str  # school_dossier, funding_dossier, recommendation_run
    entity_kind: str
    entity_id: Optional[str]
    user_id: Optional[str]

    # Entity context
    entity_name: str
    website_hint: Optional[str]
    existing_data: dict[str, Any]
    user_profile: dict[str, Any]
    program_name: Optional[str]
    degree_level: Optional[str]

    # Dossier results
    dossier_json: dict[str, Any]
    dossier_citations: list[dict]
    dossier_evidence_map: dict[str, list[str]]
    dossier_report: Optional[str]
    dossier_metrics: dict[str, Any]
    dossier_errors: list[str]

    # Validation
    citation_coverage: float
    citation_issues: list[str]

    # Scoring
    confidence: float
    promote: bool
    needs_fallback: bool

    # Fallback
    fallback_used: bool
    fallback_error: Optional[str]

    # Recommendation session (pre-created by route handler)
    recommendation_session_id: Optional[str]

    # Status
    status: str
    error: Optional[str]
    progress: list[str]
