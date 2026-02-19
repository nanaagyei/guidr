"""Stub Perplexity provider for URL discovery (returns placeholder results).

Replace with real Perplexity API when PERPLEXITY_API_KEY is configured.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.pipeline.research_gateway.providers.base import BaseResearchProvider
from src.pipeline.research_gateway.schemas import URLDiscoveryResult

logger = logging.getLogger(__name__)


class PerplexityStubProvider(BaseResearchProvider):
    """Stub that returns heuristic URLs from website_hint for testing."""

    def discover_urls(
        self,
        entity_name: str,
        category: str,
        website_hint: Optional[str] = None,
        constraints: Optional[dict] = None,
    ) -> list[URLDiscoveryResult]:
        """Generate placeholder URLs from website_hint when available."""
        results: list[URLDiscoveryResult] = []
        if not website_hint:
            logger.debug("No website_hint for %s; returning empty", entity_name)
            return results

        base = website_hint.strip()
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        base = base.rstrip("/")

        # Heuristic paths per category
        path_map = {
            "SCHOOL_OVERVIEW": ["/about", "/about-us", "/graduate", "/graduate-studies"],
            "PROGRAM_REQUIREMENTS": ["/graduate/programs", "/programs", "/academics/graduate"],
            "PROGRAM_DEADLINES": ["/admissions/deadlines", "/graduate/admissions", "/apply"],
            "PROGRAM_FUNDING": ["/funding", "/financial-aid", "/graduate/funding", "/fellowships"],
            "FACULTY_DIRECTORY": ["/people", "/faculty", "/directory", "/departments"],
            "PROFESSOR_PROFILE": [],
        }
        paths = path_map.get(category.upper(), ["/"])
        max_results = (constraints or {}).get("max_results", 5)

        now = datetime.utcnow().isoformat() + "Z"
        for i, path in enumerate(paths):
            if i >= max_results:
                break
            url = f"{base}{path}" if path != "/" else base
            results.append(
                URLDiscoveryResult(
                    url=url,
                    title=f"{entity_name} - {path or 'Home'}",
                    snippet="Stub discovery result",
                    confidence=0.7 - (i * 0.1),
                    reason="Heuristic path from website_hint",
                    source="perplexity_stub",
                    retrieved_at=now,
                )
            )
        return results
