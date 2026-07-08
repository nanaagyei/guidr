"""Google Search agent for finding school websites and program pages."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from src.config import settings
from src.scrapers.agents.tools import WebNavigationTool

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class GoogleSearchAgent:
    """Agent that uses Google search to find school websites and program pages."""

    def __init__(self):
        self.nav_tool = WebNavigationTool()
        self._groq = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key and AsyncGroq else None
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key and AsyncOpenAI else None
        self._llm_enabled = settings.enable_llm_extraction and (self._groq or self._openai)

    async def find_school_website(self, school_name: str, country: str = "") -> Optional[str]:
        """
        Use Google search to find official school website.

        Args:
            school_name: Name of the school
            country: Country of the school (optional, helps refine search)

        Returns:
            Official website URL or None if not found
        """
        # Construct search query
        query = f'"{school_name}" official website'
        if country:
            query += f" {country}"

        logger.info(f"Searching Google for: {query}")

        # Perform Google search
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        try:
            result = await self.nav_tool.run(search_url)
            if not result.get("success"):
                logger.warning(f"Failed to fetch Google search results: {result.get('error')}")
                return None

            html = result["html"]

            # Extract search results
            search_results = self._extract_google_results(html)

            if not search_results:
                logger.warning(f"No search results found for {school_name}")
                return None

            # Use LLM to select the best result
            if self._llm_enabled and len(search_results) > 1:
                best_url = await self._llm_select_best_result(school_name, search_results)
                if best_url:
                    return best_url

            # Fallback: return first result
            return search_results[0]["url"] if search_results else None

        except Exception as e:
            logger.error(f"Error searching for {school_name}: {e}")
            return None

    async def find_programs_page(self, school_name: str, website_url: str) -> Optional[str]:
        """
        Find graduate programs listing page via Google search.

        Args:
            school_name: Name of the school
            website_url: Base website URL

        Returns:
            URL of programs listing page or None
        """
        # Try searching within the school's domain first
        domain = urlparse(website_url).netloc

        query = f'site:{domain} graduate programs'
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        try:
            result = await self.nav_tool.run(search_url)
            if not result.get("success"):
                logger.warning(f"Failed to fetch Google search results: {result.get('error')}")
                return None

            html = result["html"]
            search_results = self._extract_google_results(html)

            if search_results:
                # Filter results to only include the school's domain
                domain_results = [
                    r for r in search_results
                    if urlparse(r["url"]).netloc == domain
                ]

                if domain_results:
                    # Use LLM to select best programs page
                    if self._llm_enabled:
                        best_url = await self._llm_select_programs_page(domain_results)
                        if best_url:
                            return best_url

                    return domain_results[0]["url"]

            # Fallback: try broader search
            query = f'"{school_name}" graduate programs'
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

            result = await self.nav_tool.run(search_url)
            if result.get("success"):
                html = result["html"]
                search_results = self._extract_google_results(html)

                # Filter to school's domain
                domain_results = [
                    r for r in search_results
                    if urlparse(r["url"]).netloc == domain
                ]

                if domain_results:
                    return domain_results[0]["url"]

            return None

        except Exception as e:
            logger.error(f"Error finding programs page for {school_name}: {e}")
            return None

    def _extract_google_results(self, html: str) -> List[Dict[str, str]]:
        """Extract search results from Google HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Google search results are typically in divs with class "g"
        for result_div in soup.find_all("div", class_="g"):
            # Find the link
            link_elem = result_div.find("a", href=True)
            if not link_elem:
                continue

            url = link_elem["href"]
            # Skip Google's internal links
            if url.startswith("/search") or url.startswith("/url?q="):
                continue

            # Extract title
            title_elem = result_div.find("h3")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract snippet
            snippet_elem = result_div.find("span", class_="aCOpRe") or result_div.find("div", class_="VwiC3b")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            if url and url.startswith("http"):
                results.append({
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                })

        return results[:5]  # Return top 5 results

    async def _llm_select_best_result(
        self,
        school_name: str,
        results: List[Dict[str, str]]
    ) -> Optional[str]:
        """Use LLM to select the best official website from search results."""
        if not self._llm_enabled or not results:
            return None

        # Prepare context
        results_text = "\n".join([
            f"{i+1}. {r['title']}\n   URL: {r['url']}\n   {r['snippet'][:200]}"
            for i, r in enumerate(results)
        ])

        prompt = f"""Given these Google search results for "{school_name}", select the ONE URL that is most likely the official university/school website.

Results:
{results_text}

Return ONLY the URL (starting with http:// or https://), nothing else. If no suitable official website is found, return "NONE"."""

        try:
            if self._groq:
                response = await self._groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
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
            logger.warning(f"LLM selection failed: {e}")

        return None

    async def _llm_select_programs_page(
        self,
        results: List[Dict[str, str]]
    ) -> Optional[str]:
        """Use LLM to select the best graduate programs listing page."""
        if not self._llm_enabled or not results:
            return None

        results_text = "\n".join([
            f"{i+1}. {r['title']}\n   URL: {r['url']}\n   {r['snippet'][:200]}"
            for i, r in enumerate(results)
        ])

        prompt = f"""Given these search results, select the ONE URL that is most likely a graduate programs listing page (a page that lists multiple graduate programs, not a single program page).

Results:
{results_text}

Return ONLY the URL (starting with http:// or https://), nothing else. If no suitable programs listing page is found, return "NONE"."""

        try:
            if self._groq:
                response = await self._groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
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
            logger.warning(f"LLM selection failed: {e}")

        return None

    async def close(self):
        """Clean up resources."""
        await self.nav_tool.close()
