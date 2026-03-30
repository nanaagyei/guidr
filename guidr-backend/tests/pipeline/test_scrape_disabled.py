"""Tests verifying that scraping is gracefully disabled when feature flags are off."""
from unittest.mock import MagicMock, patch

import pytest


class TestFallbackScrapeNoOp:
    """fallback_scrape node should no-op when enable_scrape_fallback=False."""

    def test_fallback_scrape_returns_noop_when_flag_false(self):
        """When scrape fallback is disabled, node returns without calling fetch_page."""
        mock_settings = MagicMock()
        mock_settings.enable_scrape_fallback = False

        state = {
            "entity_kind": "school",
            "entity_id": "some-uuid",
            "website_hint": "https://example.edu",
            "progress": [],
        }

        with patch("src.pipeline.orchestrator.dossier_nodes.settings", mock_settings):
            from src.pipeline.orchestrator.dossier_nodes import fallback_scrape
            result = fallback_scrape(state)

        assert result["fallback_used"] is False
        assert "fallback_scrape" in result["progress"]

    def test_fallback_scrape_does_not_call_fetch_page_when_disabled(self):
        """When disabled, fetch_page from nodes.py must NOT be invoked."""
        mock_settings = MagicMock()
        mock_settings.enable_scrape_fallback = False

        state = {
            "entity_kind": "school",
            "entity_id": "some-uuid",
            "website_hint": "https://example.edu",
            "progress": [],
        }

        # Patch fetch_page and extract_structured to detect if called
        with (
            patch("src.pipeline.orchestrator.dossier_nodes.settings", mock_settings),
            patch("src.pipeline.orchestrator.nodes.fetch_page") as mock_fetch,
        ):
            from src.pipeline.orchestrator.dossier_nodes import fallback_scrape
            fallback_scrape(state)

        mock_fetch.assert_not_called()


class TestPipelineTasksDisabled:
    """Bulk scraping tasks should skip gracefully when enable_bulk_scrape=False."""

    def test_run_full_pipeline_skips_when_bulk_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.pipeline_tasks.settings", mock_settings):
            from src.pipeline.tasks.pipeline_tasks import run_full_pipeline
            result = run_full_pipeline("some-institution-id")

        assert result["status"] == "skipped"
        assert result["reason"] == "bulk_scrape_disabled"

    def test_batch_scrape_skips_when_bulk_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.pipeline_tasks.settings", mock_settings):
            from src.pipeline.tasks.pipeline_tasks import batch_scrape_institutions
            result = batch_scrape_institutions(["id1", "id2", "id3"])

        assert result["status"] == "skipped"
        assert result["queued"] == 0
        assert result["skipped"] == 3

    def test_refresh_stale_skips_when_bulk_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.pipeline_tasks.settings", mock_settings):
            from src.pipeline.tasks.pipeline_tasks import refresh_stale_institutions
            result = refresh_stale_institutions()

        assert result["status"] == "skipped"


class TestScrapeTasksDisabled:
    """Individual scrape tasks should return skipped dict without touching DB or Firecrawl."""

    @pytest.fixture(autouse=True)
    def mock_session_local(self):
        """Prevent any SessionLocal() calls during tests."""
        with patch("src.pipeline.tasks.scrape_tasks.SessionLocal") as mock_sl:
            yield mock_sl

    def test_extract_funding_skips_when_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.scrape_tasks.settings", mock_settings):
            from src.pipeline.tasks.scrape_tasks import extract_funding_for_institution
            result = extract_funding_for_institution("some-id")

        assert result["status"] == "skipped"

    def test_extract_faculty_skips_when_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.scrape_tasks.settings", mock_settings):
            from src.pipeline.tasks.scrape_tasks import extract_faculty_for_institution
            result = extract_faculty_for_institution("some-id")

        assert result["status"] == "skipped"

    def test_extract_programs_skips_when_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.scrape_tasks.settings", mock_settings):
            from src.pipeline.tasks.scrape_tasks import extract_programs_for_institution
            result = extract_programs_for_institution("some-id")

        assert result["status"] == "skipped"

    def test_scrape_overview_skips_when_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with patch("src.pipeline.tasks.scrape_tasks.settings", mock_settings):
            from src.pipeline.tasks.scrape_tasks import scrape_overview_for_institution
            result = scrape_overview_for_institution("some-id")

        assert result["status"] == "skipped"

    def test_scrape_tasks_do_not_instantiate_firecrawl_when_disabled(self, mock_session_local):
        """Ensure EnhancedFirecrawlClient is never constructed when disabled."""
        mock_settings = MagicMock()
        mock_settings.enable_bulk_scrape = False

        with (
            patch("src.pipeline.tasks.scrape_tasks.settings", mock_settings),
            patch("src.pipeline.clients.firecrawl_enhanced.EnhancedFirecrawlClient") as mock_fc,
        ):
            from src.pipeline.tasks.scrape_tasks import extract_funding_for_institution
            extract_funding_for_institution("some-id")

        mock_fc.assert_not_called()
        # Verify DB session was never opened
        mock_session_local.assert_not_called()
