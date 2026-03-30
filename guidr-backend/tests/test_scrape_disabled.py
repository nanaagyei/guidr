"""Tests verifying that scraping is gracefully disabled when feature flags are off."""
import os
from unittest.mock import MagicMock, patch

import pytest

# Importing pipeline tasks pulls in src.db; keep env consistent for create_engine.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/guidr_test",
)
os.environ.setdefault(
    "JWT_SECRET",
    "test-jwt-secret-at-least-thirty-two-characters-long",
)


class TestFallbackScrapeNoOp:
    """fallback_scrape node should no-op when enable_scrape_fallback=False."""

    def test_fallback_scrape_returns_noop_when_flag_false(self):
        """When scrape fallback is disabled, node returns without calling fetch_page."""
        from src.config import settings

        state = {
            "entity_kind": "school",
            "entity_id": "some-uuid",
            "website_hint": "https://example.edu",
            "progress": [],
        }

        with patch.object(settings, "enable_scrape_fallback", False):
            from src.pipeline.orchestrator.dossier_nodes import fallback_scrape

            result = fallback_scrape(state)

        assert result["fallback_used"] is False
        assert "fallback_scrape" in result["progress"]

    def test_fallback_scrape_does_not_call_fetch_page_when_disabled(self):
        """When disabled, fetch_page from nodes.py must NOT be invoked."""
        from src.config import settings

        state = {
            "entity_kind": "school",
            "entity_id": "some-uuid",
            "website_hint": "https://example.edu",
            "progress": [],
        }

        with (
            patch.object(settings, "enable_scrape_fallback", False),
            patch("src.pipeline.orchestrator.nodes.fetch_page") as mock_fetch,
        ):
            from src.pipeline.orchestrator.dossier_nodes import fallback_scrape

            fallback_scrape(state)

        mock_fetch.assert_not_called()


class TestPipelineTasksDisabled:
    """Bulk scraping tasks should skip gracefully when enable_bulk_scrape=False."""

    def test_run_full_pipeline_skips_when_bulk_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.pipeline_tasks import run_full_pipeline

            result = run_full_pipeline.run("some-institution-id")

        assert result["status"] == "skipped"

    def test_batch_scrape_skips_when_bulk_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.pipeline_tasks import batch_scrape_institutions

            result = batch_scrape_institutions.run(["id1", "id2", "id3"])

        assert result["status"] == "skipped"
        assert result["queued"] == 0
        assert result["skipped"] == 3

    def test_refresh_stale_skips_when_bulk_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.pipeline_tasks import refresh_stale_institutions

            result = refresh_stale_institutions.run()

        assert result["status"] == "skipped"


class TestScrapeTasksDisabled:
    """Individual scrape tasks should return skipped dict without touching DB or Firecrawl."""

    @pytest.fixture(autouse=True)
    def mock_session_local(self):
        """Prevent any SessionLocal() calls during tests."""
        with patch("src.pipeline.tasks.scrape_tasks.SessionLocal") as mock_sl:
            yield mock_sl

    def test_extract_funding_skips_when_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.scrape_tasks import extract_funding_for_institution

            result = extract_funding_for_institution.run("some-id")

        assert result["status"] == "skipped"

    def test_extract_faculty_skips_when_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.scrape_tasks import extract_faculty_for_institution

            result = extract_faculty_for_institution.run("some-id")

        assert result["status"] == "skipped"

    def test_extract_programs_skips_when_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.scrape_tasks import extract_programs_for_institution

            result = extract_programs_for_institution.run("some-id")

        assert result["status"] == "skipped"

    def test_scrape_overview_skips_when_disabled(self):
        from src.config import settings

        with patch.object(settings, "enable_bulk_scrape", False):
            from src.pipeline.tasks.scrape_tasks import scrape_overview_for_institution

            result = scrape_overview_for_institution.run("some-id")

        assert result["status"] == "skipped"

    def test_scrape_tasks_do_not_instantiate_firecrawl_when_disabled(self, mock_session_local):
        """Ensure EnhancedFirecrawlClient is never constructed when disabled."""
        from src.config import settings

        with (
            patch.object(settings, "enable_bulk_scrape", False),
            patch("src.pipeline.clients.firecrawl_enhanced.EnhancedFirecrawlClient") as mock_fc,
        ):
            from src.pipeline.tasks.scrape_tasks import extract_funding_for_institution

            extract_funding_for_institution.run("some-id")

        mock_fc.assert_not_called()
        mock_session_local.assert_not_called()
