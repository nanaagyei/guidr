"""Job fingerprint computation for pipeline deduplication.

Per 23_DB_MIGRATIONS and 19_JOB_DEDUP specs.
"""
from __future__ import annotations

import hashlib
from typing import Optional


def url_hash(url: Optional[str]) -> str:
    """SHA256 hex of lowercased URL, or '-' if None/empty."""
    if not url or not url.strip():
        return "-"
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()


def compute_job_fingerprint(
    job_type: str,
    schema_version: str = "v1",
    freshness_bucket: str = "default",
    entity_kind: Optional[str] = None,
    entity_id: Optional[str] = None,
    source_url_hash: Optional[str] = None,
    target_url: Optional[str] = None,
) -> tuple[str, str]:
    """Compute deterministic job fingerprint for dedup.

    Args:
        job_type: e.g. "research_discovery", "scrape_fetch", "extract_llm"
        schema_version: schema version string
        freshness_bucket: e.g. "7d", "30d", "manual"
        entity_kind: school, program, professor, etc.
        entity_id: UUID string of entity
        source_url_hash: precomputed URL hash (optional)
        target_url: URL to hash if source_url_hash not provided

    Returns:
        (fingerprint_hex, fingerprint_input) for debugging
    """
    kind = entity_kind or "-"
    eid = (str(entity_id).strip() if entity_id else None) or "-"
    url_h = source_url_hash
    if url_h is None and target_url:
        url_h = url_hash(target_url)
    url_h = url_h or "-"

    parts = [job_type, schema_version, freshness_bucket, kind, eid, url_h]
    fingerprint_input = "|".join(parts)
    fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
    return fingerprint, fingerprint_input
