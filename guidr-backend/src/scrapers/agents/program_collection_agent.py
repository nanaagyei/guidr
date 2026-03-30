"""Program data collection agent using multiple extraction methods."""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, Optional

from src.config import settings
from src.scrapers.base import ProgramSeed
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper
from src.scrapers.agents.program_navigation_agent import ProgramNavigationAgent
from src.scrapers.browser.playwright_scraper import PlaywrightScraper
from src.models.institution import Institution

logger = logging.getLogger(__name__)


class ProgramCollectionAgent:
    """Collects detailed program information using multiple methods."""
    
    def __init__(self):
        self.firecrawl = FirecrawlScraper()
        self.nav_agent = ProgramNavigationAgent()
        self.playwright = PlaywrightScraper()
    
    async def collect_program_data(
        self,
        program_url: str,
        institution: Institution
    ) -> ProgramSeed:
        """
        Collect comprehensive program data using all available methods.
        
        Args:
            program_url: URL of the program detail page
            institution: Institution model object
            
        Returns:
            ProgramSeed with collected data
            
        Raises:
            ValueError: If the URL is invalid or returns an error page
        """
        # Quick check: skip obvious non-program URLs
        url_lower = program_url.lower()
        skip_patterns = ["/maps", "/map/", "/directions", "/campus", "/visit", "/tour"]
        if any(pattern in url_lower for pattern in skip_patterns):
            raise ValueError(f"URL appears to be a non-program page: {program_url}")
        
        data: Dict[str, Any] = {
            "name": None,
            "degree_level": None,
            "field_of_study": None,
            "description": None,
            "application_deadline_primary": None,
            "tuition_estimate_per_year": None,
            "application_fee": None,
            "website_url": program_url,
            "program_features": [],
            "data_source": "scraped",
        }
        
        # Method 1: Try Firecrawl extraction first (fastest, most reliable)
        if self.firecrawl.is_available():
            logger.info(f"Trying Firecrawl extraction for {program_url}")
            firecrawl_data = await self.extract_with_firecrawl(program_url)
            if firecrawl_data:
                data.update({k: v for k, v in firecrawl_data.items() if v is not None})
        
        # Method 2: Use LLM navigation agent (handles complex layouts)
        if not data.get("name") or not data.get("description"):
            logger.info(f"Trying LLM agent extraction for {program_url}")
            llm_data = await self.extract_with_llm_agent(program_url)
            if llm_data:
                # Merge, preferring LLM data where Firecrawl didn't find anything
                for key, value in llm_data.items():
                    if value and not data.get(key):
                        data[key] = value
        
        # Method 3: Use Playwright for dynamic content (fallback)
        if not data.get("name") or not data.get("description"):
            logger.info(f"Trying Playwright extraction for {program_url}")
            playwright_data = await self.extract_with_playwright(program_url)
            if playwright_data:
                for key, value in playwright_data.items():
                    if value and not data.get(key):
                        data[key] = value
        
        # Map LLM extractor fields to ProgramSeed fields
        # LLM extractor returns: deadline_primary (alias: application_deadline_primary), tuition
        # ProgramSeed expects: application_deadline_primary, tuition_estimate_per_year
        
        # Handle deadline field mapping
        deadline = data.get("application_deadline_primary") or data.get("deadline_primary")
        
        # Handle tuition field mapping
        tuition = data.get("tuition_estimate_per_year") or data.get("tuition")
        
        # Clean and validate program name
        raw_name = data.get("name") or ""
        program_name = self._clean_program_name(raw_name, program_url)
        
        # If we still don't have a valid name, try to extract from URL
        if not program_name or program_name.lower() in ["unknown program", "404", "page not found", "not found"]:
            program_name = self._extract_name_from_url(program_url)
        
        # If still no valid name, skip this program
        if not program_name or len(program_name.strip()) < 3:
            logger.warning(f"Could not extract valid program name from {program_url}, skipping")
            raise ValueError(f"Invalid program name extracted from {program_url}")
        
        # Convert to ProgramSeed
        return ProgramSeed(
            institution_name=institution.name,
            name=program_name,
            degree_level=data.get("degree_level") or "masters",
            field_of_study=data.get("field_of_study"),
            description=data.get("description"),
            website_url=program_url,
            application_deadline_primary=deadline,
            tuition_estimate_per_year=tuition,
            application_fee=data.get("application_fee"),
            program_features=data.get("program_features"),
            data_source="comprehensive_scraping",
        )
    
    def _clean_program_name(self, name: str, url: str) -> str:
        """Clean program name by removing page title artifacts and error messages."""
        if not name:
            return ""
        
        # Remove soft hyphens and other invisible characters
        name = "".join(char for char in name if unicodedata.category(char)[0] != "C" or char in [" ", "-", "_"])
        
        # Remove common page title separators and prefixes
        name = name.strip()
        
        # Remove "|" and everything after it (common in page titles)
        if "|" in name:
            name = name.split("|")[0].strip()
        
        # Remove " - " and everything after it
        if " - " in name:
            name = name.split(" - ")[0].strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "Home",
            "Welcome to",
            "About",
            "Error",
            "404",
            "Page Not Found",
            "Not Found",
            "the ",  # Remove lowercase "the" at start (e.g., "the New Era of...")
        ]
        for prefix in prefixes_to_remove:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
                # Remove leading punctuation
                name = name.lstrip(": -|").strip()
        
        # Capitalize first letter if it starts with lowercase (after removing "the")
        if name and name[0].islower():
            name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()
        
        # Reject common error/page titles and admissions pages
        invalid_names = [
            "404",
            "404 not found",
            "page not found",
            "not found",
            "error 404",
            "error",
            "home",
            "index",
            "catalog",
            "programs a-z",
            "programs",
            "graduate catalog",
            "graduate programs",
            "degrees",
            "graduate admissions",
            "admissions",
            "admission",
            "apply",
            "application",
        ]
        
        name_lower = name.lower()
        if any(invalid in name_lower for invalid in invalid_names):
            return ""
        
        # Reject names that are clearly page headings (start with "the", "a", "an" followed by capital)
        # But allow if it's a proper program name like "The Master of Science"
        if name_lower.startswith(("the ", "a ", "an ")) and len(name.split()) > 5:
            # Likely a heading/description, not a program name
            return ""
        
        # Reject if name is too short or looks like a description
        if len(name) < 3 or len(name) > 200:
            return ""
        
        # Reject if it looks like a sentence/description rather than a program name
        if name.count(" ") > 10:  # Too many words
            return ""
        
        # Reject taglines and marketing phrases
        tagline_patterns = [
            "world changers",
            "future makers",
            "we can imagine",
            "be the light",
            "the new era",
            "experience",
            "discover",
            "explore",
            "welcome",
            "imagine",
            "here",
        ]
        if any(tagline in name_lower for tagline in tagline_patterns):
            return ""
        
        # Reject if it looks like a heading (e.g., "the New Era of Yale Engineering")
        # These typically have "the" + adjective + "of" pattern
        words = name_lower.split()
        if len(words) >= 4 and words[0] == "the" and "of" in words:
            # Check if it's a descriptive heading vs actual program name
            # Real program names usually don't have this pattern
            return ""
        
        # Reject if it ends with a period (likely a sentence/tagline)
        if name.endswith("."):
            return ""
        
        # Reject single generic words that are likely navigation
        generic_words = ["departments", "programs", "degrees", "catalog", "admissions"]
        if name_lower in generic_words:
            return ""
        
        # Fix names that need spacing (e.g., "YaleSchoolofArt" -> "Yale School of Art")
        # Look for patterns like "Schoolof" or "Universityof"
        import re
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)  # Add space between camelCase
        name = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", name)  # Add space between ALLCAPS and TitleCase
        
        return name
    
    def _extract_name_from_url(self, url: str) -> str:
        """Try to extract a program name from the URL path."""
        from urllib.parse import urlparse
        import re
        
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        
        if not path:
            return ""
        
        # Get the last meaningful segment
        segments = [s for s in path.split("/") if s and s not in ["programs", "program", "degrees", "degree", "graduate", "grad"]]
        
        if segments:
            # Take the last segment and clean it up
            name = segments[-1]
            # Replace hyphens and underscores with spaces
            name = re.sub(r"[-_]", " ", name)
            # Capitalize words
            name = " ".join(word.capitalize() for word in name.split())
            return name
        
        return ""
    
    async def extract_with_firecrawl(self, url: str) -> Optional[Dict[str, Any]]:
        """Try Firecrawl extraction first."""
        if not self.firecrawl.is_available():
            return None
        
        try:
            result = self.firecrawl.scrape_url(url, formats=["markdown", "links"])
            if not result:
                return None
            
            markdown = result.get("markdown", "")
            
            # Check if this is an error page (404, etc.)
            if self._is_error_page(markdown):
                logger.debug(f"Skipping error page: {url}")
                return None
            
            # Use LLM to extract structured data from markdown
            if settings.enable_llm_extraction and markdown:
                extracted = await self._llm_extract_from_markdown(markdown, url)
                if extracted:
                    return extracted
            
            # Fallback: basic parsing
            return self._parse_markdown_basic(markdown)
            
        except Exception as e:
            logger.warning(f"Firecrawl extraction failed for {url}: {e}")
            return None
    
    def _is_error_page(self, content: str) -> bool:
        """Check if content indicates an error page (404, etc.)."""
        if not content:
            return False
        
        content_lower = content.lower()
        error_indicators = [
            "404",
            "page not found",
            "not found",
            "error 404",
            "the page you're looking for",
            "the requested page",
            "could not be found",
            "does not exist",
        ]
        
        # Check if multiple error indicators are present
        matches = sum(1 for indicator in error_indicators if indicator in content_lower)
        return matches >= 2  # Require at least 2 indicators to be sure
    
    async def extract_with_llm_agent(self, url: str) -> Dict[str, Any]:
        """Use LLM agent to navigate and extract program data."""
        try:
            return await self.nav_agent.navigate_and_extract(url)
        except Exception as e:
            logger.warning(f"LLM agent extraction failed for {url}: {e}")
            return {}
    
    async def extract_with_playwright(self, url: str) -> Dict[str, Any]:
        """Use Playwright for dynamic content extraction."""
        try:
            return await self.playwright.scrape_dynamic_page(url)
        except Exception as e:
            logger.warning(f"Playwright extraction failed for {url}: {e}")
            return {}
    
    async def _llm_extract_from_markdown(self, markdown: str, url: str) -> Optional[Dict[str, Any]]:
        """Use LLM to extract structured program data from markdown."""
        from src.services.llm_extractor import LLMExtractor
        
        extractor = LLMExtractor()
        try:
            # Convert markdown to HTML-like format for LLM extractor
            # (LLM extractor expects HTML, but markdown should work too)
            result = await extractor.extract_program_data(markdown, url)
            return result
        except Exception as e:
            logger.debug(f"LLM extraction from markdown failed: {e}")
            return None
    
    def _parse_markdown_basic(self, markdown: str) -> Dict[str, Any]:
        """Basic parsing of markdown content."""
        import re
        
        data: Dict[str, Any] = {}
        
        # Extract title (first H1)
        title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if title_match:
            data["name"] = title_match.group(1).strip()
        
        # Extract description (first substantial paragraph)
        paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip() and not p.startswith("#")]
        if paragraphs:
            data["description"] = paragraphs[0][:1000]
        
        # Extract deadlines
        deadline_patterns = [
            r"deadline[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
            r"application\s+due[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                data["application_deadline_primary"] = match.group(1)
                break
        
        # Extract tuition
        tuition_patterns = [
            r"\$([\d,]+(?:\.\d{2})?)\s*(?:per\s+)?(?:year|annually)",
            r"tuition[:\s]*\$([\d,]+(?:\.\d{2})?)",
        ]
        for pattern in tuition_patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    data["tuition_estimate_per_year"] = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Detect degree level
        markdown_lower = markdown.lower()
        if "ph.d" in markdown_lower or "phd" in markdown_lower or "doctoral" in markdown_lower:
            data["degree_level"] = "phd"
        elif "master" in markdown_lower or "m.s." in markdown_lower or "m.a." in markdown_lower:
            data["degree_level"] = "masters"
        
        return data
    
    async def close(self):
        """Clean up resources."""
        await self.nav_agent.close()
        await self.playwright.close()

