"""Faculty extractor for discovering and parsing professor data."""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from src.pipeline.schemas.faculty_schemas import ProfessorCreate

logger = logging.getLogger(__name__)

# URL patterns indicating faculty pages
FACULTY_URL_PATTERNS = [
    r"faculty",
    r"people",
    r"directory",
    r"professor",
    r"staff",
    r"researchers",
    r"team",
    r"our[-_]?people",
]

# Academic title normalization
TITLE_MAP = {
    "professor": "Professor",
    "prof.": "Professor",
    "prof ": "Professor",
    "associate professor": "Associate Professor",
    "assoc. professor": "Associate Professor",
    "assoc prof": "Associate Professor",
    "assistant professor": "Assistant Professor",
    "asst. professor": "Assistant Professor",
    "asst prof": "Assistant Professor",
    "adjunct professor": "Adjunct Professor",
    "visiting professor": "Visiting Professor",
    "emeritus": "Professor Emeritus",
    "lecturer": "Lecturer",
    "senior lecturer": "Senior Lecturer",
    "instructor": "Instructor",
    "research scientist": "Research Scientist",
    "postdoc": "Postdoctoral Researcher",
    "postdoctoral": "Postdoctoral Researcher",
}

# Email pattern
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Name cleaning pattern (remove prefixes like "Dr.", "Prof.")
NAME_PREFIX_PATTERN = re.compile(
    r"^(Dr\.?|Prof\.?|Professor|Mr\.?|Ms\.?|Mrs\.?)\s+", re.IGNORECASE
)


class FacultyExtractor:
    """Extract faculty/professor data from scraped web content."""

    def discover_faculty_urls(self, links: List[str]) -> List[str]:
        """Filter links to find likely faculty directory pages.

        Args:
            links: All links found on a page.

        Returns:
            Links likely pointing to faculty directories.
        """
        faculty_links = []
        for link in links:
            link_lower = link.lower()
            if any(re.search(p, link_lower) for p in FACULTY_URL_PATTERNS):
                faculty_links.append(link)
        return faculty_links

    def clean_name(self, name: str) -> str:
        """Clean and normalize a professor name.

        Args:
            name: Raw name string.

        Returns:
            Cleaned name without prefixes or extra whitespace.
        """
        name = name.strip()
        name = NAME_PREFIX_PATTERN.sub("", name)
        # Remove trailing degree suffixes
        name = re.sub(r",?\s*(Ph\.?D\.?|M\.?D\.?|Ed\.?D\.?|J\.?D\.?)\.?$", "", name, flags=re.IGNORECASE)
        # Collapse whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def normalize_title(self, title: str) -> str:
        """Normalize an academic title to a standard form.

        Args:
            title: Raw title string.

        Returns:
            Normalized title.
        """
        title_lower = title.lower().strip()
        for key, normalized in TITLE_MAP.items():
            if key in title_lower:
                return normalized
        return title.strip()

    def extract_email(self, text: str) -> Optional[str]:
        """Extract the first email address from text.

        Args:
            text: Text potentially containing an email address.

        Returns:
            Email address or None.
        """
        match = EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def parse_research_interests(self, text: str) -> List[str]:
        """Parse research interests from text.

        Handles comma-separated, semicolon-separated, and bullet-point lists.

        Args:
            text: Text containing research interests.

        Returns:
            List of individual interest strings.
        """
        if not text:
            return []

        # Try semicolon split first (more specific delimiter)
        if ";" in text:
            items = [t.strip() for t in text.split(";")]
        else:
            # Fall back to comma split
            items = [t.strip() for t in text.split(",")]

        # Clean up bullet points and numbering
        cleaned = []
        for item in items:
            item = re.sub(r"^[\-•*\d.)\]]+\s*", "", item).strip()
            if 2 <= len(item) <= 200:
                cleaned.append(item)

        return cleaned

    def extract_from_markdown(
        self, markdown: str, source_url: Optional[str] = None
    ) -> List[ProfessorCreate]:
        """Extract professor entries from a markdown faculty page.

        Uses heading-based section splitting to identify individual
        faculty members.

        Args:
            markdown: Markdown content of a faculty page.
            source_url: URL the content was scraped from.

        Returns:
            List of validated ProfessorCreate objects.
        """
        results: List[ProfessorCreate] = []
        if not markdown:
            return results

        # Split by headings (## or ### typically denote individual faculty)
        sections = re.split(r"\n#{2,4}\s+", markdown)

        for section in sections:
            section = section.strip()
            if len(section) < 10:
                continue

            lines = section.split("\n")
            name_candidate = lines[0].strip().strip("#").strip()

            # Validate name: should look like a person's name
            name_candidate = self.clean_name(name_candidate)
            if len(name_candidate) < 3 or len(name_candidate) > 300:
                continue

            # Names should contain at least a space (first + last)
            if " " not in name_candidate:
                continue

            # Skip if name looks like a section header
            skip_words = ["department", "faculty", "directory", "research", "about", "contact"]
            if any(w in name_candidate.lower() for w in skip_words):
                continue

            section_text = "\n".join(lines[1:])
            email = self.extract_email(section_text)

            # Try to find title
            title = None
            for line in lines[1:5]:
                line_lower = line.lower().strip()
                for key in TITLE_MAP:
                    if key in line_lower:
                        title = self.normalize_title(line)
                        break
                if title:
                    break

            # Extract research interests
            interests: List[str] = []
            for line in lines:
                line_lower = line.lower()
                if any(
                    kw in line_lower
                    for kw in ["research interest", "research area", "interests:", "specializ"]
                ):
                    # The interests are often on the same or next line
                    interest_text = re.sub(
                        r"^.*?(research interests?|research areas?|interests|specializ\w+)\s*:?\s*",
                        "",
                        line,
                        flags=re.IGNORECASE,
                    )
                    interests = self.parse_research_interests(interest_text)
                    break

            # Extract personal page URL from section links
            personal_url = None
            url_pattern = re.compile(r"https?://[^\s\)\"]+")
            urls_in_section = url_pattern.findall(section_text)
            for url in urls_in_section:
                if "scholar.google" in url:
                    pass  # handled below
                elif any(kw in url.lower() for kw in ["faculty", "people", "profile"]):
                    personal_url = url
                    break

            # Scholar profile
            scholar_url = None
            for url in urls_in_section:
                if "scholar.google" in url:
                    scholar_url = url
                    break

            try:
                prof = ProfessorCreate(
                    full_name=name_candidate,
                    title=title,
                    email=email,
                    personal_page_url=personal_url,
                    scholar_profile_url=scholar_url,
                    interests_tags=interests if interests else None,
                )
                results.append(prof)
            except Exception:
                logger.debug("Skipping invalid faculty: %s", name_candidate)

        return results
