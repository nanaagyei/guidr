"""Scraping orchestrator - centralizes URL discovery, robots check, and job routing.

Per Skill 06: Coordinates the full scraping workflow per institution:
1. Check robots.txt compliance
2. Discover relevant URLs via Firecrawl map
3. Categorize URLs into overview, programs, faculty, funding
4. Provide discovered URLs to scrape tasks
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.pipeline.clients.firecrawl_enhanced import EnhancedFirecrawlClient

logger = logging.getLogger(__name__)

# URL path/keyword patterns for categorization
OVERVIEW_PATTERNS = [
    r"about", r"about-us", r"about_us", r"overview", r"history",
    r"mission", r"welcome", r"home$", r"^/$",
]
PROGRAM_PATTERNS = [
    r"graduate", r"grad", r"programs?", r"masters?", r"phd", r"doctoral",
    r"degrees?", r"academics", r"departments?",
]
FACULTY_PATTERNS = [
    r"faculty", r"people", r"directory", r"professors?", r"staff",
    r"researchers?", r"team", r"our[-_]?people",
]
FUNDING_PATTERNS = [
    r"funding", r"financial[-_]?aid", r"scholarship", r"fellowship",
    r"assistantship", r"tuition", r"cost", r"stipend", r"grant",
]


@dataclass
class DiscoveredUrls:
    """Categorized URLs from a single institution domain."""

    overview: List[str] = field(default_factory=list)
    programs: List[str] = field(default_factory=list)
    faculty: List[str] = field(default_factory=list)
    funding: List[str] = field(default_factory=list)
    uncategorized: List[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    """Result of orchestrator operations."""

    success: bool
    allowed: bool = True
    crawl_delay: int = 0
    discovered: Optional[DiscoveredUrls] = None
    error: Optional[str] = None


def _matches_any(url: str, patterns: List[str]) -> bool:
    """Check if URL path matches any of the patterns."""
    url_lower = url.lower()
    for p in patterns:
        if re.search(p, url_lower):
            return True
    return False


def _categorize_url(url: str) -> str:
    """Return category: overview, programs, faculty, funding, or uncategorized."""
    if _matches_any(url, OVERVIEW_PATTERNS):
        return "overview"
    if _matches_any(url, PROGRAM_PATTERNS):
        return "programs"
    if _matches_any(url, FACULTY_PATTERNS):
        return "faculty"
    if _matches_any(url, FUNDING_PATTERNS):
        return "funding"
    return "uncategorized"


class ScrapingOrchestrator:
    """Orchestrates URL discovery and categorization for institution scraping.

    Centralizes robots.txt check and discover_graduate_pages. Scrape tasks
    can use the orchestrator instead of calling Firecrawl directly for
    consistent URL discovery and compliance.
    """

    def __init__(
        self,
        firecrawl: Optional[EnhancedFirecrawlClient] = None,
    ):
        self.firecrawl = firecrawl or EnhancedFirecrawlClient()

    def check_can_scrape(self, institution_url: str) -> OrchestratorResult:
        """Check if we are allowed to scrape this institution (robots.txt).

        Args:
            institution_url: Root URL of the institution.

        Returns:
            OrchestratorResult with allowed, crawl_delay.
        """
        if not self.firecrawl.is_available():
            return OrchestratorResult(
                success=False,
                allowed=False,
                error="Firecrawl API key not configured",
            )
        url = self.firecrawl._normalize_institution_url(institution_url)
        robots = self.firecrawl.check_robots_txt(url)
        return OrchestratorResult(
            success=True,
            allowed=robots["allowed"],
            crawl_delay=robots.get("crawl_delay", 0) or 0,
        )

    def discover_graduate_pages(
        self,
        institution_url: str,
        map_limit: int = 200,
    ) -> OrchestratorResult:
        """Discover and categorize URLs relevant to graduate school data.

        Uses Firecrawl map to get all discoverable URLs, then categorizes
        them into overview, programs, faculty, funding.

        Args:
            institution_url: Root URL of the institution.
            map_limit: Max URLs to fetch from map.

        Returns:
            OrchestratorResult with discovered URLs by category.
        """
        if not self.firecrawl.is_available():
            return OrchestratorResult(
                success=False,
                allowed=False,
                error="Firecrawl API key not configured",
            )

        url = self.firecrawl._normalize_institution_url(institution_url)

        # Check robots first
        robots = self.firecrawl.check_robots_txt(url)
        if not robots["allowed"]:
            return OrchestratorResult(
                success=False,
                allowed=False,
                error="Blocked by robots.txt",
            )

        discovered = DiscoveredUrls()

        # Map with broad search to get graduate-related URLs
        all_links = self.firecrawl.map_site(
            url,
            search="graduate program faculty funding about",
            limit=map_limit,
        )

        for link in all_links:
            cat = _categorize_url(link)
            if cat == "overview":
                discovered.overview.append(link)
            elif cat == "programs":
                discovered.programs.append(link)
            elif cat == "faculty":
                discovered.faculty.append(link)
            elif cat == "funding":
                discovered.funding.append(link)
            else:
                discovered.uncategorized.append(link)

        # Deduplicate while preserving order
        for lst in [discovered.overview, discovered.programs, discovered.faculty, discovered.funding]:
            seen = set()
            unique = []
            for u in lst:
                if u not in seen:
                    seen.add(u)
                    unique.append(u)
            lst.clear()
            lst.extend(unique)

        logger.info(
            "Discovered URLs: overview=%d programs=%d faculty=%d funding=%d",
            len(discovered.overview),
            len(discovered.programs),
            len(discovered.faculty),
            len(discovered.funding),
        )

        return OrchestratorResult(
            success=True,
            allowed=True,
            crawl_delay=robots.get("crawl_delay", 0) or 0,
            discovered=discovered,
        )
