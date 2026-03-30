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
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        expected = self._make_research_response()
        stub_provider = MagicMock()
        stub_provider.run.return_value = expected

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            request = self._make_request()
            result = svc.run(request)

            stub_provider.run.assert_called_once_with(request)
            assert result.status == "SUCCESS"

    # ------------------------------------------------------------------ #
    # 3. Successful result is cached
    # ------------------------------------------------------------------ #
    def test_result_cached_on_success(self):
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        response = self._make_research_response(status="SUCCESS")
        stub_provider = MagicMock()
        stub_provider.run.return_value = response

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            request = self._make_request()
            svc.run(request)

            # setex should be called for caching
            mock_redis.setex.assert_called_once()

    # ------------------------------------------------------------------ #
    # 4. Failed result is NOT cached
    # ------------------------------------------------------------------ #
    def test_failed_not_cached(self):
        mod = _get_mod()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        response = self._make_research_response(status="FAILED")
        stub_provider = MagicMock()
        stub_provider.run.return_value = response

        with patch.object(mod, "_select_provider", return_value=stub_provider), \
             patch.object(mod, "_get_redis", return_value=mock_redis):
            svc = mod.ResearchGatewayService()
            request = self._make_request()
            svc.run(request)

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
            request = self._make_request(job_type="URL_DISCOVERY")
            svc.run(request)

            mock_db.merge.assert_called()
            mock_db.commit.assert_called_once()

    # ------------------------------------------------------------------ #
    # 8. Stub provider selected without API key
    # ------------------------------------------------------------------ #
    def test_stub_selected_without_api_key(self):
        mod = _get_mod()
        import src.config as config_mod

        mock_settings = MagicMock()
        mock_settings.perplexity_api_key = None

        with patch.object(mod, "PerplexityStubProvider") as mock_stub_cls, \
             patch.object(config_mod, "settings", mock_settings):
            provider = mod._select_provider()

        mock_stub_cls.assert_called_once()


if __name__ == "__main__":
    unittest.main()
