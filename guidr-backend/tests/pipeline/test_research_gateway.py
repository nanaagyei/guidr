"""Tests for ResearchGatewayService: caching, provider selection, persistence."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


def _get_mod():
    """Import the service module for patch.object usage."""
    from src.pipeline.research_gateway import service as mod
    return mod


class TestResearchGatewayService(unittest.TestCase):
    """Tests for src.pipeline.research_gateway.service."""

    def _make_request(self, job_type="URL_DISCOVERY", category="SCHOOL_OVERVIEW", use_cache=True):
        from src.pipeline.research_gateway.schemas import (
            ResearchRequest,
            EntityContext,
            CacheConfig,
        )
        return ResearchRequest(
            job_type=job_type,
            entity=EntityContext(
                entity_type="SCHOOL",
                entity_id="aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee",
                name="MIT",
                website_hint="https://mit.edu",
            ),
            category=category,
            cache=CacheConfig(use_cache=use_cache, max_age_hours=168),
        )

    def _make_research_response(self, status="SUCCESS"):
        from src.pipeline.research_gateway.schemas import ResearchResponse, Metrics
        return ResearchResponse(
            status=status,
            job_type="URL_DISCOVERY",
            category="SCHOOL_OVERVIEW",
            entity={"entity_type": "SCHOOL"},
            results=[],
            metrics=Metrics(),
        )

    def _make_dossier_response(self, status="SUCCESS"):
        from src.pipeline.research_gateway.schemas import DossierResponse, Metrics
        return DossierResponse(
            status=status,
            final_json={"overview": "test data"},
            metrics=Metrics(),
        )

    def _run_with_mocks(self, response, request=None, use_cache=True):
        """Helper: run gateway with mocked provider, redis, and DB."""
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # cache miss

        stub_provider = MagicMock()
        stub_provider.run.return_value = response

        if request is None:
            request = self._make_request(use_cache=use_cache)

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            # Also mock DB cache to avoid real DB connections
            svc._db_cache_get = MagicMock(return_value=None)
            svc._db_cache_set = MagicMock()
            result = svc.run(request)

        return result, mock_redis, stub_provider, svc

    # ------------------------------------------------------------------ #
    # 1. Cache hit returns cached response
    # ------------------------------------------------------------------ #
    def test_cached_response_on_hit(self):
        mod = _get_mod()
        cached = self._make_research_response()
        mock_redis = MagicMock()
        mock_redis.get.return_value = cached.model_dump_json().encode()

        stub_provider = MagicMock()

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            request = self._make_request()
            result = svc.run(request)

            assert result.metrics.cache_hit is True
            stub_provider.run.assert_not_called()

    # ------------------------------------------------------------------ #
    # 2. Provider called on cache miss
    # ------------------------------------------------------------------ #
    def test_provider_called_on_miss(self):
        expected = self._make_research_response()
        result, _, stub_provider, _ = self._run_with_mocks(expected)

        stub_provider.run.assert_called_once()
        assert result.status == "SUCCESS"

    # ------------------------------------------------------------------ #
    # 3. Successful result is cached
    # ------------------------------------------------------------------ #
    def test_result_cached_on_success(self):
        response = self._make_research_response(status="SUCCESS")
        _, mock_redis, _, _ = self._run_with_mocks(response)

        # setex should be called for Redis caching
        mock_redis.setex.assert_called_once()

    # ------------------------------------------------------------------ #
    # 4. Failed result is NOT cached
    # ------------------------------------------------------------------ #
    def test_failed_not_cached(self):
        response = self._make_research_response(status="FAILED")
        _, mock_redis, _, _ = self._run_with_mocks(response)

        mock_redis.setex.assert_not_called()

    # ------------------------------------------------------------------ #
    # 5. Dossier job type returns DossierResponse
    # ------------------------------------------------------------------ #
    def test_dossier_type_uses_dossier_response(self):
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        dossier = self._make_dossier_response()
        stub_provider = MagicMock()
        stub_provider.run.return_value = dossier

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            from src.pipeline.research_gateway.schemas import DossierResponse

            svc = mod.ResearchGatewayService()
            svc._db_cache_get = MagicMock(return_value=None)
            svc._db_cache_set = MagicMock()
            request = self._make_request(job_type="DOSSIER_EXTRACTION")
            result = svc.run(request)

            assert isinstance(result, DossierResponse)
            assert result.status == "SUCCESS"

    # ------------------------------------------------------------------ #
    # 6. Dedupe key is deterministic
    # ------------------------------------------------------------------ #
    def test_dedupe_key_deterministic(self):
        mod = _get_mod()

        req1 = self._make_request()
        req2 = self._make_request()
        assert mod._dedupe_key(req1) == mod._dedupe_key(req2)

    # ------------------------------------------------------------------ #
    # 7. Source documents persisted for URL_DISCOVERY
    # ------------------------------------------------------------------ #
    def test_source_documents_persisted_for_url_discovery(self):
        mod = _get_mod()
        import src.db as db_mod
        from src.pipeline.research_gateway.schemas import (
            ResearchResponse,
            URLDiscoveryResult,
            Metrics,
        )

        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        response = ResearchResponse(
            status="SUCCESS",
            job_type="URL_DISCOVERY",
            category="SCHOOL_OVERVIEW",
            entity={"entity_type": "SCHOOL"},
            results=[
                URLDiscoveryResult(url="https://mit.edu/about", source="perplexity"),
            ],
            metrics=Metrics(),
        )
        stub_provider = MagicMock()
        stub_provider.run.return_value = response

        mock_db = MagicMock()

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis), \
             patch.object(db_mod, "SessionLocal", return_value=mock_db):
            svc = mod.ResearchGatewayService()
            svc._db_cache_get = MagicMock(return_value=None)
            svc._db_cache_set = MagicMock()
            request = self._make_request(job_type="URL_DISCOVERY")
            svc.run(request)

            # source_documents persist calls merge + commit
            mock_db.merge.assert_called()
            assert mock_db.commit.call_count >= 1

    # ------------------------------------------------------------------ #
    # 8. Stub provider selected without API key
    # ------------------------------------------------------------------ #
    def test_stub_selected_without_api_key(self):
        mod = _get_mod()
        import src.config as config_mod

        mock_settings = MagicMock()
        mock_settings.perplexity_api_key = None
        mock_settings.open_deep_research_api_key = None
        mock_settings.open_deep_research_base_url = None

        with patch.object(mod, "PerplexityStubProvider") as mock_stub_cls, \
             patch.object(config_mod, "settings", mock_settings):
            provider = mod._select_provider()

        mock_stub_cls.assert_called_once()

    # ------------------------------------------------------------------ #
    # 9. DB cache fallback is used when Redis misses
    # ------------------------------------------------------------------ #
    def test_db_cache_fallback_on_redis_miss(self):
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Redis miss

        cached_response = self._make_research_response()

        with patch.object(mod, "_select_provider") as mock_provider, \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            svc._db_cache_get = MagicMock(return_value=cached_response)
            request = self._make_request()
            result = svc.run(request)

        # Provider should NOT have been called — DB cache hit
        mock_provider.return_value.run.assert_not_called()
        assert result.metrics.cache_hit is True

    # ------------------------------------------------------------------ #
    # 10. Cost budget enforcement rejects over-budget requests
    # ------------------------------------------------------------------ #
    def test_budget_enforcement_rejects_over_budget(self):
        from src.pipeline.research_gateway.schemas import Budget

        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        # Use a "real-looking" provider that has non-zero cost
        stub_provider = MagicMock()
        stub_provider.__class__.__name__ = "PerplexityProvider"

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            svc._db_cache_get = MagicMock(return_value=None)

            # Create request with very low budget; perplexity tier costs 0.005/1K tokens
            # 100K tokens * 0.005/1K = $0.50 which exceeds $0.01 budget
            request = self._make_request()
            request.budget = Budget(max_tokens=100000, max_cost_usd=0.01)

            result = svc.run(request)

        assert result.status == "FAILED"
        assert any("budget" in e.lower() or "cost" in e.lower() for e in result.errors)
        stub_provider.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
