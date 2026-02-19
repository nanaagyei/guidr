"""Base provider interface for research."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.pipeline.research_gateway.schemas import (
    ResearchRequest,
    ResearchResponse,
    URLDiscoveryResult,
    Metrics,
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

    def run(self, request: ResearchRequest) -> ResearchResponse:
        """Execute research job. Default delegates to discover_urls for URL_DISCOVERY and REPAIR_EXTRACTION."""
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
