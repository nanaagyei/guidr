"""Typed state for professor match graph."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class ProfessorMatchState(TypedDict, total=False):
    """State passed between professor match graph nodes."""

    # Job identification
    job_id: str
    pipeline_job_id: Optional[str]
    entity_kind: str  # always "school" for the institution
    entity_id: Optional[str]  # institution_id
    user_id: Optional[str]

    # Context
    institution_name: str
    department: Optional[str]
    user_interests: list[str]
    openalex_institution_id: Optional[str]

    # Candidate data
    openalex_candidates: list[dict[str, Any]]
    enriched_candidates: list[dict[str, Any]]

    # Synthesis results
    ranked_professors: list[dict[str, Any]]
    synthesis_citations: list[dict]
    synthesis_evidence_map: dict[str, list[str]]

    # Status
    confidence: float
    status: str
    error: Optional[str]
    progress: list[str]
