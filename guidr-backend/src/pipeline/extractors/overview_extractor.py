"""Overview extractor for school-level metadata and statistics."""
from __future__ import annotations

import logging
import re
from typing import Optional

from src.pipeline.schemas.school_schemas import SchoolOverviewData

logger = logging.getLogger(__name__)

# Patterns for extracting numeric stats
ACCEPTANCE_RATE_PATTERN = re.compile(
    r"acceptance\s+rate[:\s]*(\d{1,3}(?:\.\d{1,2})?)\s*%", re.IGNORECASE
)
ENROLLMENT_PATTERN = re.compile(
    r"(?:total\s+)?enrollment[:\s]*([\d,]+)", re.IGNORECASE
)
GRAD_ENROLLMENT_PATTERN = re.compile(
    r"graduate\s+(?:student\s+)?enrollment[:\s]*([\d,]+)", re.IGNORECASE
)

# Campus setting keywords
CAMPUS_SETTING_MAP = {
    "urban": ["urban", "city", "metropolitan", "downtown"],
    "suburban": ["suburban", "suburb"],
    "rural": ["rural", "small town"],
}

CALENDAR_MAP = {
    "semester": ["semester", "two semesters"],
    "quarter": ["quarter", "quarters"],
    "trimester": ["trimester", "trimesters"],
}


class OverviewExtractor:
    """Extract school overview data from scraped web content."""

    def extract_acceptance_rate(self, text: str) -> Optional[float]:
        """Extract acceptance rate percentage from text.

        Args:
            text: Text content to search.

        Returns:
            Acceptance rate as a float (0-100) or None.
        """
        match = ACCEPTANCE_RATE_PATTERN.search(text)
        if match:
            rate = float(match.group(1))
            if 0 <= rate <= 100:
                return rate
        return None

    def extract_enrollment(self, text: str) -> Optional[int]:
        """Extract total enrollment from text.

        Args:
            text: Text content to search.

        Returns:
            Enrollment count or None.
        """
        match = ENROLLMENT_PATTERN.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
        return None

    def extract_grad_enrollment(self, text: str) -> Optional[int]:
        """Extract graduate enrollment from text.

        Args:
            text: Text content to search.

        Returns:
            Graduate enrollment count or None.
        """
        match = GRAD_ENROLLMENT_PATTERN.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
        return None

    def detect_campus_setting(self, text: str) -> Optional[str]:
        """Detect campus setting (urban/suburban/rural) from text.

        Args:
            text: Text content to search.

        Returns:
            Campus setting string or None.
        """
        text_lower = text.lower()
        for setting, keywords in CAMPUS_SETTING_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return setting
        return None

    def detect_academic_calendar(self, text: str) -> Optional[str]:
        """Detect academic calendar type from text.

        Args:
            text: Text content to search.

        Returns:
            Calendar type string or None.
        """
        text_lower = text.lower()
        for cal_type, keywords in CALENDAR_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return cal_type
        return None

    def extract_description(self, markdown: str, max_length: int = 2000) -> Optional[str]:
        """Extract the main descriptive text from markdown.

        Takes the first substantial paragraph as the description.

        Args:
            markdown: Full page markdown content.
            max_length: Max characters to return.

        Returns:
            Description text or None.
        """
        if not markdown:
            return None

        # Split into paragraphs and find the first substantial one
        paragraphs = re.split(r"\n\n+", markdown)
        for para in paragraphs:
            cleaned = para.strip().strip("#").strip()
            # Skip short lines, headings, nav elements
            if len(cleaned) < 100:
                continue
            if cleaned.startswith("[") or cleaned.startswith("|"):
                continue
            return cleaned[:max_length]

        return None

    def extract_from_markdown(self, markdown: str) -> SchoolOverviewData:
        """Extract all overview data from a markdown page.

        Args:
            markdown: Markdown content of a school overview page.

        Returns:
            SchoolOverviewData with all extracted fields.
        """
        if not markdown:
            return SchoolOverviewData()

        return SchoolOverviewData(
            description=self.extract_description(markdown),
            acceptance_rate=self.extract_acceptance_rate(markdown),
            enrollment_total=self.extract_enrollment(markdown),
            grad_enrollment=self.extract_grad_enrollment(markdown),
            campus_setting=self.detect_campus_setting(markdown),
            academic_calendar=self.detect_academic_calendar(markdown),
        )
