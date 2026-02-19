"""Research Gateway service: URL discovery and deep research with caching."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from src.pipeline.research_gateway.schemas import ResearchRequest, ResearchResponse
from src.pipeline.research_gateway.providers.perplexity_stub import PerplexityStubProvider

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _dedupe_key(request: ResearchRequest) -> str:
    """Compute cache dedupe key."""
    parts = [
        request.entity.entity_type,
        request.entity.entity_id or "-",
        request.category,
        "v1",
        hashlib.sha256(str(sorted(request.constraints.domains_allowlist or [])).encode()).hexdigest()[:16],
        str(request.cache.max_age_hours),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _get_redis():
    try:
        import redis
        from src.config import settings
        return redis.from_url(settings.redis_url)
    except Exception:
        return None


def _select_provider():
    """Select the best available provider: real Perplexity if API key present, stub otherwise."""
    from src.config import settings
    api_key = getattr(settings, "perplexity_api_key", None)
    if api_key:
        try:
            from src.pipeline.research_gateway.providers.perplexity import PerplexityProvider
            provider = PerplexityProvider(api_key=api_key)
            if provider.is_available():
                logger.debug("Using real Perplexity provider")
                return provider
        except ImportError:
            pass
    logger.debug("Using stub Perplexity provider")
    return PerplexityStubProvider()


class ResearchGatewayService:
    """Orchestrates research jobs via provider adapters with Redis caching."""

    def __init__(self) -> None:
        self._provider = _select_provider()

    def run(self, request: ResearchRequest) -> ResearchResponse:
        """Execute research job with cache check and budget enforcement."""
        dedupe = request.cache.dedupe_key or _dedupe_key(request)
        request.cache.dedupe_key = dedupe

        # Cache check
        if request.cache.use_cache:
            cached = self._cache_get(dedupe)
            if cached:
                logger.info("Research cache hit for %s", dedupe[:16])
                cached.metrics.cache_hit = True
                return cached

        response = self._provider.run(request)

        # Cache store on success
        if request.cache.use_cache and response.status == "SUCCESS":
            self._cache_set(dedupe, response)

        # Persist source_documents for discovered URLs
        if response.results:
            self._persist_source_documents(request, response)

        return response

    def _cache_get(self, key: str) -> Optional[ResearchResponse]:
        """Look up cached response in Redis."""
        r = _get_redis()
        if r is None:
            return None
        try:
            cache_key = f"guidr:v1:research:cache:{key}"
            raw = r.get(cache_key)
            if raw:
                return ResearchResponse.model_validate_json(raw)
        except Exception as exc:
            logger.debug("Research cache get failed: %s", exc)
        return None

    def _cache_set(self, key: str, response: ResearchResponse) -> None:
        """Store response in Redis with TTL."""
        r = _get_redis()
        if r is None:
            return
        try:
            cache_key = f"guidr:v1:research:cache:{key}"
            r.setex(cache_key, CACHE_TTL_SECONDS, response.model_dump_json())
        except Exception as exc:
            logger.debug("Research cache set failed: %s", exc)

    def _persist_source_documents(
        self, request: ResearchRequest, response: ResearchResponse
    ) -> None:
        """Save discovered URLs as source_documents (best-effort)."""
        entity_id = request.entity.entity_id
        if not entity_id:
            return
        try:
            import uuid
            from src.db import SessionLocal
            from src.models.source_document import SourceDocument

            db = SessionLocal()
            try:
                for result in response.results[:5]:
                    doc = SourceDocument(
                        entity_kind=request.entity.entity_type.lower(),
                        entity_id=uuid.UUID(entity_id),
                        canonical_url=result.url,
                        purpose=request.category,
                        discovered_by=result.source or "research_gateway",
                    )
                    db.merge(doc)
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.debug("source_document persist failed: %s", exc)
            finally:
                db.close()
        except Exception:
            pass
