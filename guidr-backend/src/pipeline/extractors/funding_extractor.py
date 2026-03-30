"""Funding opportunity extractor for discovering and parsing financial aid data."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.pipeline.schemas.funding_schemas import (
    AmountPeriod,
    FundingOpportunityCreate,
    FundingType,
)

logger = logging.getLogger(__name__)

# URL patterns indicating funding pages
FUNDING_URL_PATTERNS = [
    r"financial[-_]?aid",
    r"funding",
    r"fellowship",
    r"scholarship",
    r"assistantship",
    r"tuition[-_]?waiver",
    r"stipend",
    r"grant",
    r"financial[-_]?support",
    r"cost",
]

# Keywords for classifying funding types
FUNDING_TYPE_KEYWORDS = {
    FundingType.FELLOWSHIP: [
        "fellowship", "fellow", "predoctoral", "postdoctoral",
    ],
    FundingType.ASSISTANTSHIP: [
        "assistantship", "teaching assistant", "research assistant",
        "ta position", "ra position", "graduate assistant",
    ],
    FundingType.SCHOLARSHIP: [
        "scholarship", "merit award", "merit-based", "academic award",
    ],
    FundingType.GRANT: [
        "grant", "research grant", "travel grant", "dissertation grant",
    ],
    FundingType.WAIVER: [
        "tuition waiver", "fee waiver", "tuition remission",
        "tuition reduction",
    ],
}

# Regex for parsing dollar amounts
AMOUNT_PATTERN = re.compile(
    r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:[-–]\s*\$?\s*([\d,]+(?:\.\d{2})?))?",
)


class FundingExtractor:
    """Extract funding opportunities from scraped web content."""

    def discover_funding_urls(self, links: List[str]) -> List[str]:
        """Filter a list of URLs to find likely funding-related pages.

        Args:
            links: All links found on a page.

        Returns:
            Links that likely point to funding information.
        """
        funding_links = []
        for link in links:
            link_lower = link.lower()
            if any(re.search(p, link_lower) for p in FUNDING_URL_PATTERNS):
                funding_links.append(link)
        return funding_links

    def classify_funding_type(self, text: str) -> FundingType:
        """Classify funding type based on text content.

        Args:
            text: Name or description text.

        Returns:
            Best-matching FundingType.
        """
        text_lower = text.lower()
        for ftype, keywords in FUNDING_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return ftype
        return FundingType.SCHOLARSHIP  # default

    def parse_amount(
        self, text: str
    ) -> tuple[Optional[float], Optional[float]]:
        """Extract dollar amounts from text.

        Args:
            text: Text potentially containing dollar amounts.

        Returns:
            Tuple of (amount_min, amount_max). Both may be None.
        """
        match = AMOUNT_PATTERN.search(text)
        if not match:
            return None, None
        amount_min = float(match.group(1).replace(",", ""))
        if match.group(2):
            amount_max = float(match.group(2).replace(",", ""))
        else:
            amount_max = amount_min
        return amount_min, amount_max

    def detect_amount_period(self, text: str) -> Optional[AmountPeriod]:
        """Detect whether an amount is annual, per semester, etc.

        Args:
            text: Surrounding text for context.

        Returns:
            AmountPeriod or None.
        """
        text_lower = text.lower()
        if any(w in text_lower for w in ["per year", "annual", "yearly", "/year", "/yr"]):
            return AmountPeriod.ANNUAL
        if any(w in text_lower for w in ["per semester", "/semester"]):
            return AmountPeriod.SEMESTER
        if any(w in text_lower for w in ["per month", "monthly", "/month", "/mo"]):
            return AmountPeriod.MONTHLY
        if any(w in text_lower for w in ["one-time", "one time", "lump sum"]):
            return AmountPeriod.ONE_TIME
        return None

    def extract_from_markdown(
        self, markdown: str, source_url: Optional[str] = None
    ) -> List[FundingOpportunityCreate]:
        """Extract funding opportunities from a markdown page.

        Uses heuristic paragraph splitting and keyword matching to find
        individual funding items within a page of content.

        Args:
            markdown: Markdown content of a funding page.
            source_url: URL the content was scraped from.

        Returns:
            List of validated FundingOpportunityCreate objects.
        """
        results: List[FundingOpportunityCreate] = []
        if not markdown:
            return results

        # Split by headings or double newlines to get sections
        sections = re.split(r"\n#{1,4}\s+|\n\n+", markdown)

        for section in sections:
            section = section.strip()
            if len(section) < 20:
                continue

            # Look for a name-like first line
            lines = section.split("\n")
            name_candidate = lines[0].strip().strip("#").strip()
            if len(name_candidate) < 3 or len(name_candidate) > 500:
                continue

            # Must contain a funding-related keyword somewhere
            section_lower = section.lower()
            is_funding = any(
                kw in section_lower
                for keywords in FUNDING_TYPE_KEYWORDS.values()
                for kw in keywords
            )
            if not is_funding:
                continue

            funding_type = self.classify_funding_type(section)
            amount_min, amount_max = self.parse_amount(section)
            period = self.detect_amount_period(section)

            covers_tuition = any(
                w in section_lower for w in ["tuition", "tuition covered", "full tuition"]
            )
            covers_stipend = any(
                w in section_lower for w in ["stipend", "living allowance"]
            )

            try:
                item = FundingOpportunityCreate(
                    name=name_candidate,
                    funding_type=funding_type,
                    amount_min=amount_min,
                    amount_max=amount_max,
                    amount_period=period,
                    description=section[:2000] if len(section) > 2000 else section,
                    website_url=source_url,
                    source_url=source_url,
                    covers_tuition=covers_tuition if covers_tuition else None,
                    covers_stipend=covers_stipend if covers_stipend else None,
                )
                results.append(item)
            except Exception:
                logger.debug("Skipping invalid funding item: %s", name_candidate)

        return results
