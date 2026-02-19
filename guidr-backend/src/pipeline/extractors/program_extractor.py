"""Program extractor for discovering and parsing graduate program data."""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import List, Optional

from src.pipeline.schemas.program_schemas import ProgramExtractionData

logger = logging.getLogger(__name__)

DEGREE_KEYWORDS = {
    "phd": ["phd", "ph.d", "doctorate", "doctoral"],
    "masters": ["master", "m.s", "m.s.", "ms ", "ma ", "m.a", "m.a.", "masters"],
    "professional": ["jd", "mba", "md", "dds", "professional degree"],
    "certificate": ["certificate", "certification"],
}

# Patterns for common fields
DEADLINE_PATTERN = re.compile(
    r"(?:deadline|due|apply by)[:\s]*(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
GPA_PATTERN = re.compile(
    r"(?:gpa|grade point average)[:\s]*(\d\.\d{1,2})\s*(?:minimum|min\.?|or above)?",
    re.IGNORECASE,
)
GRE_PATTERN = re.compile(
    r"\b(gre\s+required|gre\s+optional|gre\s+waived|no\s+gre)\b",
    re.IGNORECASE,
)
TUITION_PATTERN = re.compile(
    r"\$\s*([\d,]+)(?:\.\d{2})?\s*(?:per\s+year|/year|/yr|annual)?",
    re.IGNORECASE,
)
DURATION_PATTERN = re.compile(
    r"(\d{1,2})\s*(?:months?|months|mo\.?)\b|(\d)\s*years?\b",
    re.IGNORECASE,
)


class ProgramExtractor:
    """Extract graduate program data from scraped web content."""

    def detect_degree_level(self, text: str) -> Optional[str]:
        """Detect degree level from text."""
        text_lower = text.lower()
        for level, keywords in DEGREE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return level
        return None

    def extract_deadline(self, text: str) -> Optional[date]:
        """Extract application deadline from text."""
        match = DEADLINE_PATTERN.search(text)
        if not match:
            return None
        try:
            from datetime import datetime
            raw = match.group(1).strip()
            for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%m/%d/%y"):
                try:
                    dt = datetime.strptime(raw.replace(",", ""), fmt)
                    return dt.date()
                except ValueError:
                    continue
        except Exception:
            pass
        return None

    def extract_gpa(self, text: str) -> Optional[float]:
        """Extract minimum GPA from text."""
        match = GPA_PATTERN.search(text)
        if match:
            try:
                val = float(match.group(1))
                if 0 <= val <= 4.0:
                    return val
            except ValueError:
                pass
        return None

    def extract_gre_required(self, text: str) -> Optional[bool]:
        """Extract GRE requirement from text."""
        match = GRE_PATTERN.search(text)
        if not match:
            return None
        phrase = match.group(1).lower()
        if "required" in phrase:
            return True
        if "optional" in phrase or "waived" in phrase or "no gre" in phrase:
            return False
        return None

    def extract_tuition(self, text: str) -> Optional[float]:
        """Extract tuition estimate from text."""
        match = TUITION_PATTERN.search(text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                pass
        return None

    def extract_duration_months(self, text: str) -> Optional[int]:
        """Extract program duration in months."""
        match = DURATION_PATTERN.search(text)
        if match:
            if match.group(1):
                try:
                    return int(match.group(1))
                except (ValueError, TypeError):
                    pass
            if match.group(2):
                try:
                    return int(match.group(2)) * 12
                except (ValueError, TypeError):
                    pass
        return None

    def extract_from_markdown(
        self,
        markdown: str,
        source_url: Optional[str] = None,
    ) -> List[ProgramExtractionData]:
        """Extract program entries from a markdown program page.

        Uses heading-based section splitting to identify individual programs.

        Args:
            markdown: Markdown content of a program listing page.
            source_url: URL the content was scraped from.

        Returns:
            List of ProgramExtractionData.
        """
        results: List[ProgramExtractionData] = []
        if not markdown or len(markdown) < 50:
            return results

        sections = re.split(r"\n#{1,4}\s+|\n##\s+|\n###\s+", markdown)

        for section in sections:
            section = section.strip()
            if len(section) < 30:
                continue

            lines = section.split("\n")
            name_candidate = lines[0].strip().strip("#").strip()
            if len(name_candidate) < 3 or len(name_candidate) > 400:
                continue

            # Skip obvious non-program headers
            skip = ["apply", "admission", "contact", "home", "menu", "about us"]
            if any(s in name_candidate.lower() for s in skip):
                continue

            degree_level = self.detect_degree_level(section) or "masters"
            deadline = self.extract_deadline(section)
            gpa = self.extract_gpa(section)
            gre = self.extract_gre_required(section)
            tuition = self.extract_tuition(section)
            duration = self.extract_duration_months(section)

            # Build description from first substantial paragraph
            desc_lines = [l.strip() for l in lines[1:6] if len(l.strip()) > 20]
            description = " ".join(desc_lines)[:1500] if desc_lines else None

            try:
                prog = ProgramExtractionData(
                    name=name_candidate,
                    degree_level=degree_level,
                    description=description,
                    duration_months=duration,
                    gre_required=gre,
                    minimum_gpa=gpa,
                    application_deadline_primary=deadline,
                    tuition_estimate_per_year=tuition,
                    website_url=source_url,
                )
                results.append(prog)
            except Exception:
                logger.debug("Skip invalid program: %s", name_candidate[:50])

        return results
