"""Unit tests for EnhancedFirecrawlClient (mocked HTTP)."""
import pytest
from unittest.mock import MagicMock, patch

from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient


class TestEnhancedFirecrawlClient:
    def test_is_available_without_api_key(self):
        with patch("src.pipeline.clients.firecrawl_enhanced.settings") as mock_settings:
            mock_settings.firecrawl_api_key = None
            client = EnhancedFirecrawlClient(api_key=None)
            assert client.is_available() is False

    def test_is_available_with_api_key(self):
        client = EnhancedFirecrawlClient(api_key="test-key")
        assert client.is_available() is True

    def test_check_robots_txt_returns_allowed_by_default(self):
        with patch("src.pipeline.clients.firecrawl_enhanced.RobotFileParser") as mock_rp:
            mock_rp.return_value.read.side_effect = Exception("No robots.txt")
            client = EnhancedFirecrawlClient(api_key="test-key")
            result = client.check_robots_txt("https://example.edu/about")
            assert result["allowed"] is True
            assert result["crawl_delay"] == 0

    def test_check_robots_txt_when_disallowed(self):
        with patch("src.pipeline.clients.firecrawl_enhanced.RobotFileParser") as MockRFP:
            rp_instance = MagicMock()
            rp_instance.can_fetch.return_value = False
            rp_instance.crawl_delay.return_value = None
            MockRFP.return_value = rp_instance
            with patch("src.pipeline.clients.firecrawl_enhanced.settings") as mock_settings:
                mock_settings.scraper_user_agent = "GuidrBot/1.0"
                client = EnhancedFirecrawlClient(api_key="test-key")
                result = client.check_robots_txt("https://example.edu/")
                assert result["allowed"] is False

    def test_normalize_institution_url_adds_https(self):
        client = EnhancedFirecrawlClient(api_key="test-key")
        assert client._normalize_institution_url("stanford.edu") == "https://stanford.edu"
        assert client._normalize_institution_url("https://stanford.edu") == "https://stanford.edu"

    def test_map_site_returns_empty_when_unavailable(self):
        with patch("src.pipeline.clients.firecrawl_enhanced.settings") as mock_settings:
            mock_settings.firecrawl_api_key = None
            client = EnhancedFirecrawlClient(api_key=None)
            result = client.map_site("https://example.edu")
            assert result == []

    def test_scrape_url_returns_none_when_unavailable(self):
        with patch("src.pipeline.clients.firecrawl_enhanced.settings") as mock_settings:
            mock_settings.firecrawl_api_key = None
            client = EnhancedFirecrawlClient(api_key=None)
            result = client.scrape_url("https://example.edu")
            assert result is None
