"""Enricher: add computed fields and metadata to pipeline data.

Adds: source_url, scraped_at, computed fields (e.g. duration in months).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DataEnricher:
    """Enriches transformed data with metadata and computed fields."""

    def enrich_funding(
        self,
        data: Dict[str, Any],
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add metadata to funding data."""
        out = dict(data)
        out.setdefault("source_url", source_url)
        out.setdefault("data_source", "pipeline_scrape")
        return out

    def enrich_program(
        self,
        data: Dict[str, Any],
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add metadata to program data."""
        out = dict(data)
        out.setdefault("website_url", source_url)
        out.setdefault("data_source", "pipeline_scrape")
        # Ensure degree_level has a value
        out.setdefault("degree_level", "masters")
        return out

    def enrich_faculty(
        self,
        data: Dict[str, Any],
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add metadata to faculty data."""
        out = dict(data)
        out.setdefault("personal_page_url", source_url)
        return out

    def enrich_overview(
        self,
        data: Dict[str, Any],
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add metadata to overview data."""
        out = dict(data)
        return out
