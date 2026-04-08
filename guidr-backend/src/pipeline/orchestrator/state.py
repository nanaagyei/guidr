"""Typed state for orchestrator graph."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class OrchestratorState(TypedDict, total=False):
    """State passed between graph nodes (TypedDict for LangGraph)."""

    job_id: str
    entity_kind: str
    entity_id: Optional[str]
    category: str
    priority: str
    schema_version: str

    entity_name: str
    website_hint: Optional[str]

    known_sources: list[dict]
    need_discovery: bool

    candidate_urls: list[str]

    target_url: Optional[str]
    raw_content: Optional[str]
    raw_artifact_id: Optional[str]

    extracted: Optional[dict[str, Any]]

    validation_errors: list[str]
    validation_warnings: list[str]
    validation_passed: bool
    confidence: float

    promote: bool
    repair: bool
    retry_count: int
    max_attempts: int
    status: str
    error: Optional[str]

    progress: list[str]

    # Phase 3 additions
    pipeline_job_id: Optional[str]
    source_document_id: Optional[str]
    extraction_run_id: Optional[str]
    fetched_at: Optional[str]  # ISO datetime string
    content_hash: Optional[str]
