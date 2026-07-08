"""LangChain-powered agent for intelligent web scraping."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.config import settings
from src.services.llm_extractor import LLMExtractor
from src.scrapers.agents.tools import (
    WebNavigationTool,
    LinkExtractorTool,
    HTMLParserTool,
    ProgramDataExtractorTool,
    TableExtractorTool,
)

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None  # type: ignore

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class SchoolScraperAgent:
    """
    Intelligent agent for scraping graduate program information.

    Uses LLM to:
    1. Navigate to relevant pages
    2. Extract program listings
    3. Parse individual program details
    4. Validate and structure data
    """

    def __init__(self, extractor: Optional[LLMExtractor] = None) -> None:
        self.extractor = extractor or LLMExtractor()
        self.nav_tool = WebNavigationTool()
        self.link_tool = LinkExtractorTool()
        self.parser_tool = HTMLParserTool()
        self.program_tool = ProgramDataExtractorTool()
        self.table_tool = TableExtractorTool()

        # LLM clients
        self._groq = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key and AsyncGroq else None
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and AsyncOpenAI else None
        self._llm_enabled = settings.enable_llm_extraction and (self._groq or self._openai)

        # Rate limiting
        self._last_request = 0.0
        self._delay = settings.scraper_delay_seconds

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)
        self._last_request = time.time()

    async def extract_programs_from_html(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract program data from HTML using LLM or fallback."""
        if not settings.enable_llm_extraction:
            raise RuntimeError("LLM extraction disabled via configuration.")
        return await self.extractor.extract_program_data(html_content=html_content, url=url)

    async def find_program_listing_page(self, institution_url: str) -> Optional[str]:
        """
        Use LLM to intelligently find the graduate programs listing page.

        Args:
            institution_url: Base URL of the institution

        Returns:
            URL of the programs listing page, or None if not found
        """
        await self._rate_limit()

        # Fetch the main page
        result = await self.nav_tool.run(institution_url)
        if not result.get("success"):
            logger.warning(f"Failed to fetch {institution_url}: {result.get('error')}")
            return None

        # Extract all links
        links = self.link_tool.run(
            result["html"],
            result["url"],
            pattern=r"(graduate|program|degree|masters?|phd|doctoral|admission)"
        )

        if not links:
            # Try broader pattern
            links = self.link_tool.run(result["html"], result["url"])

        if not links:
            return None

        # Use LLM to find best link
        if self._llm_enabled:
            try:
                best_url = await self._llm_select_best_link(links, "graduate programs listing")
                if best_url:
                    return best_url
            except Exception as e:
                logger.warning(f"LLM link selection failed: {e}")

        # Fallback: look for common patterns
        priority_patterns = [
            r"graduate.*program",
            r"program.*graduate",
            r"degrees.*offered",
            r"academic.*program",
        ]

        for pattern in priority_patterns:
            import re
            for link in links:
                if re.search(pattern, link["url"] + " " + link["text"], re.IGNORECASE):
                    return link["url"]

        return None

    async def scrape_program_listing(self, listing_url: str) -> List[Dict[str, Any]]:
        """
        Scrape program listing page to get individual program URLs.

        Args:
            listing_url: URL of the programs listing page

        Returns:
            List of program info dicts with urls
        """
        await self._rate_limit()

        result = await self.nav_tool.run(listing_url)
        if not result.get("success"):
            return []

        html = result["html"]
        base_url = result["url"]

        programs = []

        # Try extracting from table first
        table_data = self.table_tool.run(html)
        if table_data:
            for row in table_data:
                programs.append({
                    "name": row.get("Program") or row.get("Name") or row.get("col_0"),
                    "degree": row.get("Degree") or row.get("Level") or row.get("col_1"),
                    "url": None,  # May not have URL in table
                })

        # Extract links to program pages
        program_links = self.link_tool.run(
            html,
            base_url,
            pattern=r"(program|degree|masters?|phd|ms-|ma-|doctoral)"
        )

        for link in program_links:
            # Check if this looks like a program page
            if any(keyword in link["text"].lower() for keyword in
                   ["master", "phd", "doctoral", "ms ", "ma ", "program"]):
                programs.append({
                    "name": link["text"],
                    "url": link["url"],
                })

        # Deduplicate by URL
        seen_urls = set()
        unique_programs = []
        for p in programs:
            url = p.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_programs.append(p)
            elif not url:
                unique_programs.append(p)

        return unique_programs[:50]  # Limit to prevent runaway scraping

    async def scrape_program_details(self, program_url: str) -> Dict[str, Any]:
        """
        Scrape detailed information from a single program page.

        Args:
            program_url: URL of the program detail page

        Returns:
            Extracted program data
        """
        await self._rate_limit()

        result = await self.nav_tool.run(program_url)
        if not result.get("success"):
            return {"error": result.get("error"), "url": program_url}

        html = result["html"]

        # First try heuristic extraction
        data = self.program_tool.run(html, program_url)

        # If LLM is available, enhance with LLM extraction
        if self._llm_enabled:
            try:
                llm_data = await self.extractor.extract_program_data(html, program_url)
                # Merge, preferring LLM data where available
                for key, value in llm_data.items():
                    if value and (not data.get(key) or llm_data.get("confidence_score", 0) > 0.5):
                        data[key] = value
            except Exception as e:
                logger.warning(f"LLM extraction failed for {program_url}: {e}")

        return data

    async def scrape_institution_programs(
        self,
        institution_url: str,
        max_programs: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full workflow: find and scrape all graduate programs for an institution.

        Args:
            institution_url: Base URL of the institution
            max_programs: Maximum programs to scrape

        Returns:
            List of program data dicts
        """
        logger.info(f"Starting program scrape for {institution_url}")

        # Step 1: Find programs listing page
        listing_url = await self.find_program_listing_page(institution_url)
        if not listing_url:
            logger.warning(f"Could not find program listing for {institution_url}")
            return []

        logger.info(f"Found program listing: {listing_url}")

        # Step 2: Get list of programs
        program_list = await self.scrape_program_listing(listing_url)
        logger.info(f"Found {len(program_list)} programs")

        # Step 3: Scrape individual program pages
        programs = []
        for i, prog in enumerate(program_list[:max_programs]):
            if prog.get("url"):
                logger.info(f"Scraping program {i+1}/{min(len(program_list), max_programs)}: {prog.get('name')}")
                details = await self.scrape_program_details(prog["url"])
                if "error" not in details:
                    programs.append(details)

        logger.info(f"Successfully scraped {len(programs)} programs from {institution_url}")
        return programs

    async def _llm_select_best_link(
        self,
        links: List[Dict[str, str]],
        goal: str
    ) -> Optional[str]:
        """Use LLM to select the best link for a given goal."""
        if not self._llm_enabled or len(links) == 0:
            return None

        # Prepare context (limit to avoid token overflow)
        link_context = "\n".join([
            f"- {l['text'][:100]}: {l['url']}"
            for l in links[:30]
        ])

        prompt = f"""Given these links from a university website, select the ONE link most likely to lead to a {goal} page.

Links:
{link_context}

Return ONLY the URL, nothing else. If no suitable link exists, return "NONE"."""

        try:
            if self._groq:
                response = await self._groq.chat.completions.create(
                    model="llama-3.1-8b-instant",  # Updated from decommissioned llama3-8b-8192
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=500,
                )
                result = response.choices[0].message.content.strip()
            elif self._openai:
                response = await self._openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=500,
                )
                result = response.choices[0].message.content.strip()
            else:
                return None

            if result and result != "NONE" and result.startswith("http"):
                return result
        except Exception as e:
            logger.warning(f"LLM link selection error: {e}")

        return None

    async def close(self):
        """Clean up resources."""
        await self.nav_tool.close()
