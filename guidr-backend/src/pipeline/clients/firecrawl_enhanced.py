"""Enhanced Firecrawl client with map_site, extraction schemas, and pipeline methods.

Extends the patterns from the existing FirecrawlScraper in src/scrapers/schools/
with additional capabilities for the pipeline:
  - map_site() for URL discovery
  - Structured extraction schemas for funding/faculty pages
  - Dedicated methods for funding and faculty scraping
  - robots.txt compliance check before scraping
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class EnhancedFirecrawlClient:
    """Pipeline-oriented Firecrawl client with URL mapping and extraction schemas."""

    FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 2.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
        delay: Optional[float] = None,
    ):
        self.api_key = api_key or settings.firecrawl_api_key
        self.timeout = timeout
        self.delay = delay or settings.scraper_delay_seconds
        self._client = httpx.Client(timeout=timeout)
        self._last_request_time = 0.0

    def is_available(self) -> bool:
        """Check if Firecrawl API key is configured."""
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def check_robots_txt(self, url: str) -> Dict[str, Any]:
        """Check if scraping is allowed by robots.txt.

        Args:
            url: Full URL to check (e.g., https://stanford.edu/graduate/funding).

        Returns:
            Dict with 'allowed' (bool) and 'crawl_delay' (int, seconds). If robots.txt
            cannot be fetched or parsed, defaults to allowed=True, crawl_delay=0.
        """
        result: Dict[str, Any] = {"allowed": True, "crawl_delay": 0}
        try:
            parsed = urlparse(url)
            base = f"{parsed.scheme or 'https'}://{parsed.netloc}"
            robots_url = urljoin(base, "/robots.txt")
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            ua = settings.scraper_user_agent
            if not rp.can_fetch(ua, url):
                result["allowed"] = False
                logger.info("robots.txt disallows %s for %s", url, ua)
            crawl_delay = rp.crawl_delay(ua)
            if crawl_delay is not None:
                result["crawl_delay"] = int(crawl_delay)
        except Exception as exc:
            logger.debug("Could not check robots.txt for %s: %s", url, exc)
        return result

    def _normalize_institution_url(self, url: str) -> str:
        """Ensure URL has scheme for robots.txt and scraping."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url.rstrip("/")

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        retry_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single URL.

        Args:
            url: URL to scrape.
            formats: Output formats (default: markdown + links).
            retry_count: Current retry attempt.

        Returns:
            Scraped data dict or None.
        """
        if not self.is_available():
            logger.warning("Firecrawl API key not configured")
            return None

        formats = formats or ["markdown", "links"]
        self._rate_limit()

        try:
            resp = self._client.post(
                f"{self.FIRECRAWL_API_URL}/scrape",
                headers=self._headers(),
                json={"url": url, "formats": formats},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                return data.get("data", {})
            logger.warning("Firecrawl scrape failed for %s: %s", url, data.get("error"))
            return None
        except httpx.HTTPStatusError as exc:
            return self._handle_http_error(
                exc, url, lambda rc: self.scrape_url(url, formats, rc), retry_count
            )
        except Exception as exc:
            logger.error("Firecrawl error for %s: %s", url, exc)
            return None

    def map_site(
        self,
        url: str,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[str]:
        """Discover URLs on a site using Firecrawl's map endpoint.

        Args:
            url: Root URL of the site.
            search: Optional keyword to filter discovered URLs.
            limit: Maximum number of URLs to return.

        Returns:
            List of discovered URLs.
        """
        if not self.is_available():
            return []

        self._rate_limit()

        payload: Dict[str, Any] = {"url": url, "limit": limit}
        if search:
            payload["search"] = search

        try:
            resp = self._client.post(
                f"{self.FIRECRAWL_API_URL}/map",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                return data.get("links", [])
            logger.warning("Firecrawl map failed for %s: %s", url, data.get("error"))
            return []
        except Exception as exc:
            logger.error("Firecrawl map error for %s: %s", url, exc)
            return []

    def scrape_urls(
        self,
        urls: List[str],
        require_markdown: bool = False,
    ) -> List[Dict[str, Any]]:
        """Scrape a list of URLs. No discovery or robots check.

        Use when orchestrator has already discovered URLs.

        Args:
            urls: URLs to scrape.
            require_markdown: If True, only include results with markdown.

        Returns:
            List of scraped page dicts with source_url set.
        """
        results = []
        for url in urls:
            data = self.scrape_url(url)
            if data:
                data["source_url"] = url
                if not require_markdown or data.get("markdown"):
                    results.append(data)
        return results

    # ------------------------------------------------------------------
    # Pipeline convenience methods
    # ------------------------------------------------------------------

    def scrape_funding_pages(
        self,
        institution_url: str,
        pre_discovered_urls: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Discover and scrape funding-related pages for an institution.

        Args:
            institution_url: Root URL of the institution website.
            pre_discovered_urls: Optional URLs from orchestrator (skips discovery).

        Returns:
            List of scraped page data dicts (markdown + links).
        """
        if pre_discovered_urls:
            return self.scrape_urls(pre_discovered_urls, require_markdown=False)

        institution_url = self._normalize_institution_url(institution_url)
        robots = self.check_robots_txt(institution_url)
        if not robots["allowed"]:
            logger.info("Skipping funding scrape: blocked by robots.txt")
            return []
        if robots.get("crawl_delay", 0) > 0:
            time.sleep(robots["crawl_delay"])

        funding_urls = self.map_site(
            institution_url, search="funding financial aid scholarship fellowship"
        )
        if not funding_urls:
            # Fallback: try a direct scrape of common paths
            for suffix in [
                "/financial-aid",
                "/funding",
                "/admissions/financial-aid",
                "/graduate/funding",
            ]:
                candidate = institution_url.rstrip("/") + suffix
                funding_urls.append(candidate)

        results = []
        for url in funding_urls[:10]:  # cap at 10 pages
            data = self.scrape_url(url)
            if data:
                data["source_url"] = url
                results.append(data)
        return results

    def scrape_faculty_pages(
        self,
        institution_url: str,
        pre_discovered_urls: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Discover and scrape faculty directory pages.

        Args:
            institution_url: Root URL of the institution website.
            pre_discovered_urls: Optional URLs from orchestrator (skips discovery).

        Returns:
            List of scraped page data dicts.
        """
        if pre_discovered_urls:
            return self.scrape_urls(pre_discovered_urls, require_markdown=False)

        institution_url = self._normalize_institution_url(institution_url)
        robots = self.check_robots_txt(institution_url)
        if not robots["allowed"]:
            logger.info("Skipping faculty scrape: blocked by robots.txt")
            return []
        if robots.get("crawl_delay", 0) > 0:
            time.sleep(robots["crawl_delay"])

        faculty_urls = self.map_site(
            institution_url, search="faculty directory people professors"
        )
        if not faculty_urls:
            for suffix in [
                "/faculty",
                "/people",
                "/directory",
                "/about/faculty",
            ]:
                candidate = institution_url.rstrip("/") + suffix
                faculty_urls.append(candidate)

        results = []
        for url in faculty_urls[:10]:
            data = self.scrape_url(url)
            if data:
                data["source_url"] = url
                results.append(data)
        return results

    def scrape_overview_page(
        self, institution_url: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape the main overview / about page for an institution.

        Args:
            institution_url: Root URL.

        Returns:
            Scraped page data or None.
        """
        institution_url = self._normalize_institution_url(institution_url)
        robots = self.check_robots_txt(institution_url)
        if not robots["allowed"]:
            logger.info("Skipping overview scrape: blocked by robots.txt")
            return None
        if robots.get("crawl_delay", 0) > 0:
            time.sleep(robots["crawl_delay"])

        for suffix in ["", "/about", "/about-us"]:
            url = institution_url.rstrip("/") + suffix
            data = self.scrape_url(url)
            if data and data.get("markdown"):
                data["source_url"] = url
                return data
        return None

    def scrape_program_pages(
        self,
        institution_url: str,
        limit: int = 15,
        pre_discovered_urls: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Discover and scrape graduate program pages for an institution.

        Args:
            institution_url: Root URL of the institution website.
            limit: Maximum number of program pages to scrape.
            pre_discovered_urls: Optional URLs from orchestrator (skips discovery).

        Returns:
            List of scraped page data dicts.
        """
        if pre_discovered_urls:
            return self.scrape_urls(pre_discovered_urls[:limit], require_markdown=True)

        institution_url = self._normalize_institution_url(institution_url)
        robots = self.check_robots_txt(institution_url)
        if not robots["allowed"]:
            logger.info("Skipping program scrape: blocked by robots.txt")
            return []
        if robots.get("crawl_delay", 0) > 0:
            time.sleep(robots["crawl_delay"])

        program_urls = self.map_site(
            institution_url,
            search="graduate program masters phd degree",
        )
        if not program_urls:
            for suffix in [
                "/graduate/programs",
                "/programs",
                "/academics/graduate",
                "/graduate",
            ]:
                candidate = institution_url.rstrip("/") + suffix
                program_urls.append(candidate)

        results = []
        for url in program_urls[:limit]:
            data = self.scrape_url(url)
            if data and data.get("markdown"):
                data["source_url"] = url
                results.append(data)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_http_error(
        self,
        exc: httpx.HTTPStatusError,
        url: str,
        retry_fn,
        retry_count: int,
    ):
        status = exc.response.status_code
        if status == 429 and retry_count < self.MAX_RETRIES:
            backoff = self.INITIAL_BACKOFF * (2 ** retry_count)
            logger.warning(
                "Rate limited (429) for %s, retrying in %ss (attempt %d/%d)",
                url, backoff, retry_count + 1, self.MAX_RETRIES,
            )
            time.sleep(backoff)
            return retry_fn(retry_count + 1)
        if status == 403:
            logger.warning("Blocked (403) for %s", url)
            return None
        logger.error("HTTP %d for %s: %s", status, url, exc)
        return None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
