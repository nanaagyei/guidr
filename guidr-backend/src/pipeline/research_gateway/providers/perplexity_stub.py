"""Stub Perplexity provider for URL discovery (returns placeholder results).

Replace with real Perplexity API when PERPLEXITY_API_KEY is configured.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.pipeline.research_gateway.providers.base import BaseResearchProvider
from src.pipeline.research_gateway.schemas import (
    DossierCitation,
    DossierResponse,
    Metrics,
    ResearchRequest,
    URLDiscoveryResult,
)

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

    def extract_dossier(
        self,
        request: ResearchRequest,
        prompt: str,
    ) -> DossierResponse:
        """Return synthetic dossier data for dev/test environments."""
        entity_name = request.entity.name or "Unknown"
        category = request.category or ""

        # Vary stub data by category
        if "funding" in category.lower():
            final_json = {
                "fellowships": [
                    {"name": f"{entity_name} Graduate Fellowship", "amount": "$25,000/year",
                     "deadline": "January 15", "eligibility": "Full-time PhD students"},
                ],
                "assistantships": [
                    {"type": "TA", "stipend": "$20,000/year", "tuition_waiver": True},
                ],
                "scholarships": [],
            }
        elif "recommendation" in category.lower():
            final_json = {
                "recommendations": [
                    {
                        "school_name": "Massachusetts Institute of Technology",
                        "program_name": "MS in Computer Science",
                        "tier": "dream",
                        "score": 92,
                        "explanation": "World-class CS program with strong AI research labs [c1]",
                        "funding_summary": "Full funding via RA/TA for admitted students",
                        "deadline": "December 15",
                        "website_url": "https://www.eecs.mit.edu/academics/graduate-programs/",
                    },
                    {
                        "school_name": "Stanford University",
                        "program_name": "MS in Computer Science",
                        "tier": "dream",
                        "score": 90,
                        "explanation": "Top-tier program with extensive industry connections [c1]",
                        "funding_summary": "TA/RA positions available; external fellowships encouraged",
                        "deadline": "December 1",
                        "website_url": "https://cs.stanford.edu/admissions/graduate",
                    },
                    {
                        "school_name": "University of Washington",
                        "program_name": "MS in Computer Science & Engineering",
                        "tier": "reach",
                        "score": 82,
                        "explanation": "Strong research output in ML and systems [c1]",
                        "funding_summary": "RA/TA funding for qualified applicants",
                        "deadline": "December 15",
                        "website_url": "https://www.cs.washington.edu/academics/graduate",
                    },
                    {
                        "school_name": "Georgia Institute of Technology",
                        "program_name": "MS in Computer Science",
                        "tier": "target",
                        "score": 75,
                        "explanation": "Flexible specializations and affordable tuition [c1]",
                        "funding_summary": "GRA positions and fellowships available",
                        "deadline": "February 1",
                        "website_url": "https://www.cc.gatech.edu/ms-computer-science",
                    },
                    {
                        "school_name": "University of Illinois Urbana-Champaign",
                        "program_name": "MS in Computer Science",
                        "tier": "target",
                        "score": 73,
                        "explanation": "Highly ranked with diverse research areas [c1]",
                        "funding_summary": "TA/RA funding for most admitted students",
                        "deadline": "December 15",
                        "website_url": "https://cs.illinois.edu/admissions/graduate",
                    },
                ],
                "tier_counts": {"dream": 2, "reach": 1, "target": 2, "safety": 0},
                "methodology": "Programs selected based on field alignment, research strength, and funding availability (stub data).",
            }
        else:
            # School dossier / default
            final_json = {
                "overview": f"{entity_name} is a research university (stub data).",
                "acceptance_rate": "25%",
                "programs_offered": ["Computer Science", "Data Science"],
                "application_deadline": "December 15",
                "tuition_estimate": "$45,000/year",
            }

        stub_citation = DossierCitation(
            id="c1",
            url=request.entity.website_hint or f"https://www.example.edu/{entity_name.lower().replace(' ', '-')}",
            title=f"{entity_name} (stub)",
            snippet="Synthetic stub data for development testing",
            publisher="perplexity_stub",
        )

        # Build evidence_map pointing first field to the stub citation
        first_key = next(iter(final_json), "overview")
        evidence_map = {first_key: ["c1"]}

        logger.info("PerplexityStubProvider.extract_dossier returning stub for %s", entity_name)

        return DossierResponse(
            status="SUCCESS",
            final_json=final_json,
            report_markdown=f"# {entity_name} Dossier (Stub)\n\nThis is synthetic data from PerplexityStubProvider.",
            citations=[stub_citation],
            evidence_map=evidence_map,
            metrics=Metrics(latency_ms=50, cost_usd=0.0, cache_hit=False),
            errors=[],
        )
