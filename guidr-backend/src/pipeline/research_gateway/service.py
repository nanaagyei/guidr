"""Research Gateway service: URL discovery and deep research with caching."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from src.pipeline.research_gateway.schemas import (
    ResearchRequest,
    ResearchResponse,
    DossierResponse,
    Metrics,
    DOSSIER_JOB_TYPES,
)
from src.pipeline.research_gateway.providers.perplexity_stub import PerplexityStubProvider

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days

# Category-specific TTLs (seconds)
CATEGORY_TTL = {
    "recommendation_run": 7 * 24 * 3600,
    "school_dossier": 30 * 24 * 3600,
    "professor_matches": 30 * 24 * 3600,
    "funding_dossier": 14 * 24 * 3600,
}

# Estimated cost per 1K tokens by provider tier (conservative upper bounds).
_COST_PER_1K_TOKENS: dict[str, float] = {
    "perplexity": 0.005,
    "open_deep_research": 0.003,
    "stub": 0.0,
}


def _dedupe_key(request: ResearchRequest) -> str:
    """Compute cache dedupe key."""
    parts = [
        request.entity.entity_type,
        request.entity.entity_id or "-",
        request.job_type,
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
    """Select the best available provider with tiered fallback.

    Tier 1: Real Perplexity Sonar (if PERPLEXITY_API_KEY set)
    Tier 2: OpenAI-compatible deep research (if OPEN_DEEP_RESEARCH_API_KEY + _BASE_URL set)
    Tier 3: Stub provider (always available, returns synthetic data)
    """
    from src.config import settings

    # Tier 1: Real Perplexity
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

    # Tier 2: Open Deep Research (OpenAI-compatible)
    odr_key = getattr(settings, "open_deep_research_api_key", None)
    odr_url = getattr(settings, "open_deep_research_base_url", None)
    if odr_key and odr_url:
        try:
            from src.pipeline.research_gateway.providers.open_deep_research import OpenDeepResearchProvider
            provider = OpenDeepResearchProvider(api_key=odr_key, base_url=odr_url)
            if provider.is_available():
                logger.debug("Using OpenDeepResearch provider")
                return provider
        except ImportError:
            pass

    # Tier 3: Stub
    logger.debug("Using stub Perplexity provider")
    return PerplexityStubProvider()


def _provider_tier_name(provider) -> str:
    """Return a cost-tier key for the provider instance."""
    cls_name = type(provider).__name__.lower()
    if "perplexity" in cls_name and "stub" not in cls_name:
        return "perplexity"
    if "deep" in cls_name or "openai" in cls_name:
        return "open_deep_research"
    return "stub"


class ResearchGatewayService:
    """Orchestrates research jobs via provider adapters with Redis + DB caching."""

    def __init__(self) -> None:
        self._provider = _select_provider()

    def run(self, request: ResearchRequest) -> Union[ResearchResponse, DossierResponse]:
        """Execute research job with cache check, budget enforcement, and ranking."""
        dedupe = request.cache.dedupe_key or _dedupe_key(request)
        request.cache.dedupe_key = dedupe

        is_dossier = request.job_type in DOSSIER_JOB_TYPES

        # Cache check — Redis first, then DB fallback
        if request.cache.use_cache:
            cached = self._cache_get(dedupe, is_dossier=is_dossier)
            if cached:
                logger.info("Research cache hit for %s", dedupe[:16])
                cached.metrics.cache_hit = True
                return cached

        # Cost budget enforcement
        budget_error = self._check_budget(request)
        if budget_error:
            return budget_error

        response = self._provider.run(request)

        # Cache store on success
        if request.cache.use_cache and response.status == "SUCCESS":
            ttl = CATEGORY_TTL.get(request.category, CACHE_TTL_SECONDS)
            self._cache_set(dedupe, response, request=request, ttl=ttl)

        # Rank URL results for non-dossier URL_DISCOVERY responses
        if (
            not is_dossier
            and isinstance(response, ResearchResponse)
            and response.results
            and request.job_type == "URL_DISCOVERY"
        ):
            from src.pipeline.research_gateway.url_ranker import rank_url_results

            response.results = rank_url_results(
                results=response.results,
                category=request.category,
                allowlist=request.constraints.domains_allowlist or [],
            )

        # Persist source_documents for discovered URLs (non-dossier only)
        if not is_dossier and isinstance(response, ResearchResponse) and response.results:
            self._persist_source_documents(request, response)

        return response

    # ------------------------------------------------------------------
    # Budget enforcement
    # ------------------------------------------------------------------

    def _check_budget(
        self, request: ResearchRequest
    ) -> Optional[Union[ResearchResponse, DossierResponse]]:
        """Return a FAILED response if estimated cost exceeds the budget."""
        from src.config import settings

        max_tokens = request.budget.max_tokens
        tier = _provider_tier_name(self._provider)
        cost_per_1k = _COST_PER_1K_TOKENS.get(tier, 0.005)
        estimated_cost = (max_tokens / 1000) * cost_per_1k

        # Apply server-side hard cap
        hard_cap = getattr(settings, "max_research_cost_usd", 5.0)
        effective_limit = min(request.budget.max_cost_usd, hard_cap)

        if estimated_cost > effective_limit:
            msg = (
                f"Estimated cost ${estimated_cost:.4f} exceeds budget "
                f"${effective_limit:.4f} (tokens={max_tokens}, tier={tier})"
            )
            logger.warning("Budget exceeded: %s", msg)

            is_dossier = request.job_type in DOSSIER_JOB_TYPES
            if is_dossier:
                return DossierResponse(
                    status="FAILED",
                    errors=[msg],
                    metrics=Metrics(),
                )
            return ResearchResponse(
                status="FAILED",
                job_type=request.job_type,
                category=request.category,
                errors=[msg],
                metrics=Metrics(),
            )
        return None

    # ------------------------------------------------------------------
    # Caching: Redis primary + DB fallback
    # ------------------------------------------------------------------

    def _cache_get(
        self, key: str, is_dossier: bool = False
    ) -> Optional[Union[ResearchResponse, DossierResponse]]:
        """Look up cached response: Redis first, then DB fallback."""
        # Try Redis
        r = _get_redis()
        if r is not None:
            try:
                cache_key = f"guidr:v1:research:cache:{key}"
                raw = r.get(cache_key)
                if raw:
                    if is_dossier:
                        return DossierResponse.model_validate_json(raw)
                    return ResearchResponse.model_validate_json(raw)
            except Exception as exc:
                logger.debug("Research Redis cache get failed: %s", exc)

        # Fallback to DB
        return self._db_cache_get(key, is_dossier)

    def _cache_set(
        self,
        key: str,
        response: Union[ResearchResponse, DossierResponse],
        request: Optional[ResearchRequest] = None,
        ttl: int = CACHE_TTL_SECONDS,
    ) -> None:
        """Store response in both Redis and DB."""
        response_json = response.model_dump_json()

        # Redis
        r = _get_redis()
        if r is not None:
            try:
                cache_key = f"guidr:v1:research:cache:{key}"
                r.setex(cache_key, ttl, response_json)
            except Exception as exc:
                logger.debug("Research Redis cache set failed: %s", exc)

        # DB (best-effort)
        self._db_cache_set(key, response, request=request, ttl=ttl)

    def _db_cache_get(
        self, key: str, is_dossier: bool = False
    ) -> Optional[Union[ResearchResponse, DossierResponse]]:
        """Fallback: read from research_cache table."""
        try:
            from src.db import SessionLocal
            from src.models.research_cache import ResearchCache

            db = SessionLocal()
            try:
                row = (
                    db.query(ResearchCache)
                    .filter(ResearchCache.dedupe_key == key)
                    .first()
                )
                if row is None:
                    return None

                # Check expiry
                if row.expires_at and row.expires_at < datetime.now(timezone.utc):
                    return None

                result_json = json.dumps(row.latest_result_json)
                if is_dossier:
                    return DossierResponse.model_validate_json(result_json)
                return ResearchResponse.model_validate_json(result_json)
            except Exception as exc:
                logger.debug("Research DB cache get failed: %s", exc)
                return None
            finally:
                db.close()
        except Exception:
            return None

    def _db_cache_set(
        self,
        key: str,
        response: Union[ResearchResponse, DossierResponse],
        request: Optional[ResearchRequest] = None,
        ttl: int = CACHE_TTL_SECONDS,
    ) -> None:
        """Best-effort write to research_cache table."""
        try:
            from src.db import SessionLocal
            from src.models.research_cache import ResearchCache

            now = datetime.now(timezone.utc)
            expires = now + timedelta(seconds=ttl)
            result_dict = response.model_dump()

            entity_type = ""
            entity_id = None
            category = ""
            job_type = ""
            cost_usd = None

            if request:
                entity_type = request.entity.entity_type
                entity_id_str = request.entity.entity_id
                entity_id = uuid.UUID(entity_id_str) if entity_id_str else None
                category = request.category
                job_type = request.job_type

            if response.metrics and response.metrics.cost_usd:
                cost_usd = response.metrics.cost_usd

            citations = []
            if hasattr(response, "citations"):
                citations = [c.model_dump() for c in response.citations]

            db = SessionLocal()
            try:
                existing = (
                    db.query(ResearchCache)
                    .filter(ResearchCache.dedupe_key == key)
                    .first()
                )
                if existing:
                    existing.latest_result_json = result_dict
                    existing.citations_json = citations
                    existing.computed_at = now
                    existing.expires_at = expires
                    existing.cost_usd = cost_usd
                    existing.provider_name = _provider_tier_name(self._provider)
                else:
                    row = ResearchCache(
                        dedupe_key=key,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        category=category,
                        job_type=job_type,
                        latest_result_json=result_dict,
                        citations_json=citations,
                        provider_name=_provider_tier_name(self._provider),
                        cost_usd=cost_usd,
                        computed_at=now,
                        expires_at=expires,
                    )
                    db.add(row)
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.debug("Research DB cache set failed: %s", exc)
            finally:
                db.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Source document persistence
    # ------------------------------------------------------------------

    def _persist_source_documents(
        self, request: ResearchRequest, response: ResearchResponse
    ) -> None:
        """Save discovered URLs as source_documents (best-effort)."""
        entity_id = request.entity.entity_id
        if not entity_id:
            return
        try:
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
