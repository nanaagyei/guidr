"""Research Gateway: URL discovery and deep research for pipeline."""
from src.pipeline.research_gateway.errors import ResearchProviderUnavailable
from src.pipeline.research_gateway.service import (
    ResearchGatewayService,
    research_provider_available,
)
from src.pipeline.research_gateway.schemas import (
    ResearchRequest,
    ResearchResponse,
    URLDiscoveryResult,
)

__all__ = [
    "ResearchGatewayService",
    "ResearchProviderUnavailable",
    "ResearchRequest",
    "ResearchResponse",
    "URLDiscoveryResult",
    "research_provider_available",
]
