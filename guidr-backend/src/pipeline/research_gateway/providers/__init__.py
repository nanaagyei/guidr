"""Research provider adapters."""
from src.pipeline.research_gateway.providers.base import BaseResearchProvider
from src.pipeline.research_gateway.providers.perplexity_stub import PerplexityStubProvider

__all__ = ["BaseResearchProvider", "PerplexityStubProvider"]
