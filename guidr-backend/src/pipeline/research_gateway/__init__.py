"""Research Gateway: URL discovery and deep research for pipeline."""
from src.pipeline.research_gateway.service import ResearchGatewayService
from src.pipeline.research_gateway.schemas import (
    ResearchRequest,
    ResearchResponse,
    URLDiscoveryResult,
)

__all__ = [
    "ResearchGatewayService",
    "ResearchRequest",
    "ResearchResponse",
    "URLDiscoveryResult",
]
