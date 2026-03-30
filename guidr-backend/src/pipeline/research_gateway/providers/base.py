"""Base provider interface for research."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.pipeline.research_gateway.schemas import (
    ResearchRequest,
    ResearchResponse,
    DossierResponse,
    URLDiscoveryResult,
    Metrics,
    DOSSIER_JOB_TYPES,
)


class BaseResearchProvider(ABC):
    """Interface for URL discovery and deep research providers."""

    @abstractmethod
    def discover_urls(
        self,
        entity_name: str,
        category: str,
        website_hint: Optional[str] = None,
        constraints: Optional[dict] = None,
    ) -> list[URLDiscoveryResult]:
        """Discover and rank canonical URLs for an entity and category."""
        ...

    def extract_dossier(
        self,
        request: ResearchRequest,
        prompt: str,
    ) -> DossierResponse:
        """Extract a structured dossier via agentic research.

        Subclasses should override this to call their LLM with the prompt
        and return a DossierResponse with citations and evidence_map.
        """
        return DossierResponse(
            status="FAILED",
            errors=[f"extract_dossier not implemented for {type(self).__name__}"],
        )

    def run(self, request: ResearchRequest) -> ResearchResponse | DossierResponse:
        """Execute research job. Routes dossier types to extract_dossier."""
        if request.job_type in DOSSIER_JOB_TYPES:
            prompt = request.prompt_override or ""
            return self.extract_dossier(request, prompt)

        if request.job_type in ("URL_DISCOVERY", "REPAIR_EXTRACTION"):
            results = self.discover_urls(
                entity_name=request.entity.name or "Unknown",
                category=request.category,
                website_hint=request.entity.website_hint,
                constraints=request.constraints.model_dump() if request.constraints else None,
            )
            return ResearchResponse(
                status="SUCCESS" if results else "PARTIAL",
                job_type=request.job_type,
                category=request.category,
                entity=request.entity.model_dump(),
                results=results,
                citations=[],
                metrics=Metrics(cache_hit=False),
            )
        return ResearchResponse(
            status="FAILED",
            job_type=request.job_type,
            category=request.category,
            entity=request.entity.model_dump(),
            errors=[f"Job type {request.job_type} not implemented"],
        )
