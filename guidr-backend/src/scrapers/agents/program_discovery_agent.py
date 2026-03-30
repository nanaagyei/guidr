"""Intelligent program discovery agent for finding all graduate programs."""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from src.config import settings
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper
from src.scrapers.agents.google_search_agent import GoogleSearchAgent
from src.scrapers.agents.school_scraper_agent import SchoolScraperAgent
from src.scrapers.agents.tools import WebNavigationTool, LinkExtractorTool

logger = logging.getLogger(__name__)


class ProgramDiscoveryAgent:
    """Intelligently finds all graduate programs for a school."""
    
    def __init__(self):
        self.firecrawl = FirecrawlScraper()
        self.google_agent = GoogleSearchAgent()
        self.school_agent = SchoolScraperAgent()
        self.nav_tool = WebNavigationTool()
        self.link_tool = LinkExtractorTool()
    
    async def discover_programs(self, institution_name: str, institution_url: str) -> List[str]:
        """
        Discover all graduate program URLs for an institution.
        
        Args:
            institution_name: Name of the institution
            institution_url: Base URL of the institution
            
        Returns:
            List of program detail page URLs
        """
        program_urls: List[str] = []
        
        # Method 1: Try Firecrawl crawl of known program URLs
        if self.firecrawl.is_available():
            logger.info(f"Trying Firecrawl crawl for {institution_name}")
            firecrawl_urls = await self._discover_with_firecrawl(institution_url)
            program_urls.extend(firecrawl_urls)
        
        # Method 2: Find program listing page and extract URLs
        logger.info(f"Finding program listing page for {institution_name}")
        listing_page = await self.find_program_listing_page(institution_url)
        if listing_page:
            listing_urls = await self.extract_program_urls(listing_page, institution_url)
            program_urls.extend(listing_urls)
        
        # Method 3: Google search for programs
        logger.info(f"Searching Google for programs at {institution_name}")
        google_urls = await self._discover_with_google(institution_name, institution_url)
        program_urls.extend(google_urls)
        
        # Deduplicate and validate URLs
        unique_urls = self._deduplicate_urls(program_urls, institution_url)
        
        logger.info(f"Discovered {len(unique_urls)} unique program URLs for {institution_name}")
        return unique_urls
    
    async def find_program_listing_page(self, institution_url: str) -> Optional[str]:
        """
        Intelligently find the programs listing page using multiple methods.
        
        Args:
            institution_url: Base URL of the institution
            
        Returns:
            URL of programs listing page or None
        """
        # Method 1: Use existing school scraper agent
        listing_url = await self.school_agent.find_program_listing_page(institution_url)
        if listing_url:
            return listing_url
        
        # Method 2: Try common paths
        common_paths = [
            "/graduate-programs",
            "/graduate/programs",
            "/programs",
            "/degrees",
            "/academics/programs",
            "/graduate-studies",
            "/grad-programs",
        ]
        
        for path in common_paths:
            url = urljoin(institution_url, path)
            try:
                result = await self.nav_tool.run(url)
                if result.get("success"):
                    # Check if this looks like a programs listing page
                    html = result["html"]
                    if self._is_program_listing_page(html):
                        return url
            except Exception as e:
                logger.debug(f"Failed to check {url}: {e}")
        
        # Method 3: Use Google search
        domain = urlparse(institution_url).netloc
        listing_url = await self.google_agent.find_programs_page(domain, institution_url)
        if listing_url:
            return listing_url
        
        return None
    
    def _is_program_listing_page(self, html: str) -> bool:
        """Check if HTML content looks like a program listing page."""
        html_lower = html.lower()
        
        # Indicators of a program listing page
        indicators = [
            "graduate program",
            "master's program",
            "phd program",
            "doctoral program",
            "degree program",
            "program listing",
            "programs offered",
        ]
        
        indicator_count = sum(1 for indicator in indicators if indicator in html_lower)
        
        # Should have multiple program-related keywords
        return indicator_count >= 2
    
    async def extract_program_urls(self, listing_page_url: str, base_url: str) -> List[str]:
        """
        Extract program detail page URLs from listing page.
        
        Args:
            listing_page_url: URL of the programs listing page
            base_url: Base URL of the institution (for validation)
            
        Returns:
            List of program detail page URLs
        """
        program_urls: List[str] = []
        
        try:
            result = await self.nav_tool.run(listing_page_url)
            if not result.get("success"):
                return []
            
            html = result["html"]
            base_url_parsed = urlparse(base_url)
            listing_url_parsed = urlparse(listing_page_url)
            
            # Get base domain (without subdomain) for matching
            base_domain = self._get_base_domain(base_url_parsed.netloc)
            
            # Extract all links
            links = self.link_tool.run(html, listing_page_url)
            logger.debug(f"Found {len(links)} total links on {listing_page_url}")
            
            # Filter links that look like program pages
            for link in links:
                url = link["url"]
                text = link["text"].lower()
                
                # Must be from same base domain (allow subdomains)
                url_parsed = urlparse(url)
                url_domain = self._get_base_domain(url_parsed.netloc)
                
                if url_domain != base_domain:
                    continue
                
                # Check if URL or text suggests it's a program page
                if self._is_program_url(url, text):
                    program_urls.append(url)
                    logger.debug(f"Found program URL: {url} (text: {link['text'][:50]})")
            
            # Also try Firecrawl if available
            if self.firecrawl.is_available():
                try:
                    result = self.firecrawl.scrape_url(listing_page_url, formats=["links", "markdown"])
                    if result:
                        # Firecrawl links format
                        firecrawl_links = result.get("links", [])
                        if isinstance(firecrawl_links, list):
                            for link in firecrawl_links:
                                # Handle different link formats
                                if isinstance(link, dict):
                                    url = link.get("url") or link.get("href", "")
                                elif isinstance(link, str):
                                    url = link
                                else:
                                    continue
                                
                                if url and self._is_program_url(url, ""):
                                    url_parsed = urlparse(url)
                                    url_domain = self._get_base_domain(url_parsed.netloc)
                                    if url_domain == base_domain:
                                        program_urls.append(url)
                                        logger.debug(f"Found program URL from Firecrawl: {url}")
                        
                        # Also try extracting from markdown using LLM
                        markdown = result.get("markdown", "")
                        if markdown and len(program_urls) == 0:
                            logger.info("No links found via patterns, trying LLM extraction from markdown")
                            llm_urls = await self._extract_program_urls_with_llm(markdown, listing_page_url, base_domain)
                            program_urls.extend(llm_urls)
                            
                except Exception as e:
                    logger.debug(f"Firecrawl link extraction failed: {e}")
            
            # If still no programs found, try LLM extraction from HTML
            if len(program_urls) == 0:
                logger.info("No programs found via link extraction, trying LLM extraction from HTML")
                llm_urls = await self._extract_program_urls_with_llm(html, listing_page_url, base_domain)
                program_urls.extend(llm_urls)
            
        except Exception as e:
            logger.error(f"Error extracting program URLs from {listing_page_url}: {e}")
        
        logger.info(f"Extracted {len(program_urls)} program URLs from {listing_page_url}")
        return list(set(program_urls))  # Deduplicate
    
    def _get_base_domain(self, netloc: str) -> str:
        """Extract base domain from netloc (handles subdomains)."""
        # Remove port if present
        netloc = netloc.split(":")[0]
        
        # Split by dots and get last 2 parts (e.g., stanford.edu from gradadmissions.stanford.edu)
        parts = netloc.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return netloc
    
    def _is_program_url(self, url: str, text: str) -> bool:
        """Check if URL or text suggests it's a program page."""
        url_lower = url.lower()
        combined = f"{url_lower} {text}".lower()
        
        # Strong negative indicators (definitely exclude these)
        strong_negative_patterns = [
            r"/maps?",
            r"/map/",
            r"/directions",
            r"/location",
            r"/campus",
            r"/visit",
            r"/tour",
            r"/admissions?",
            r"/admission/",
            r"/apply",
            r"/application",
            r"/how-to-apply",
            r"/requirements",
            r"/deadline",
            r"/tuition",
            r"/cost",
            r"/fees",
            r"/financial-aid",
            r"/funding",
            r"/scholarship",
            r"/news/",
            r"/events/",
            r"/faculty/",
            r"/staff/",
            r"/people/",
            r"/contact/",
            r"/about/",
            r"/home",
            r"/index",
            r"/search",
            r"/calendar",
            r"/directory",
            r"/library",
            r"/housing",
            r"/dining",
            r"/parking",
            r"/transportation",
            r"/undergraduate",
            r"/undergrad",
            r"/non-degree",
            r"/certificate",
            r"/continuing-education",
            r"#",  # Skip anchors
        ]
        
        # Check strong negative patterns first (these are definitely not program pages)
        for pattern in strong_negative_patterns:
            if re.search(pattern, combined):
                logger.debug(f"Excluding URL (negative pattern): {url} (pattern: {pattern})")
                return False
        
        # Skip if it's just the listing page itself or catalog pages
        listing_page_patterns = [
            r"/programs?/?$",
            r"/graduate-programs?/?$",
            r"/degrees?/?$",
            r"/academics?/?$",
            r"/graduate/?$",
            r"/graduate-studies/?$",
            r"/catalog/",  # Catalog pages are listings, not individual programs
            r"/departments?/?$",  # Department listing pages
            r"/gsc\.",  # Graduate Student Center (not a program)
            r"gsc\.upenn\.edu",  # Specific exclusion
            r"valuing-grad-students",  # General info page
            r"provost\.upenn\.edu/graduate-admissions",  # Admissions page
        ]
        for pattern in listing_page_patterns:
            if re.search(pattern, url_lower):
                logger.debug(f"Excluding URL (listing page): {url}")
                return False
        
        # Positive indicators (must have at least one)
        positive_patterns = [
            r"/program/",  # More specific - requires /program/ not just /program
            r"/degree/",
            r"/graduate/",
            r"/masters?/",
            r"/phd/",
            r"/doctoral/",
            r"/ms[-_]",
            r"/ma[-_]",
            r"/m\.?s\.?c",
            r"/m\.?a\.?",
            r"/m\.?eng",
            r"/mba/",
            r"/department/",  # Department pages often list programs
            r"/school/",  # School pages (e.g., School of Engineering)
        ]
        
        # Check positive patterns
        has_positive = False
        for pattern in positive_patterns:
            if re.search(pattern, url_lower):
                has_positive = True
                break
        
        # Also check text for program-related keywords (but be more strict)
        if not has_positive:
            program_keywords = ["master", "phd", "doctoral", "graduate program", "degree program"]
            text_has_keyword = any(keyword in text for keyword in program_keywords)
            
            # Text must be substantial and contain program keywords
            if text_has_keyword and len(text) > 10:
                # But exclude if it's clearly navigation or general info
                exclude_keywords = ["home", "about", "contact", "apply", "admission", "visit", "campus"]
                if not any(exclude in text for exclude in exclude_keywords):
                    has_positive = True
        
        if not has_positive:
            logger.debug(f"Excluding URL (no positive indicators): {url}")
            return False
        
        # Additional validation: URL should have some depth (not just root or shallow paths)
        # Exclude very shallow paths that are likely navigation
        path_depth = len([p for p in urlparse(url).path.split("/") if p])
        if path_depth < 2:
            # Very shallow paths are usually not program pages
            # Exception: if it's clearly a program subdomain or has strong positive indicators
            # But exclude common non-program subdomains
            excluded_subdomains = ["gsc", "catalog", "provost", "admissions", "admission"]
            subdomain = urlparse(url).netloc.split(".")[0].lower()
            if subdomain in excluded_subdomains:
                logger.debug(f"Excluding URL (excluded subdomain): {url}")
                return False
            if not any(pattern in url_lower for pattern in ["program", "degree", "graduate", "phd", "masters"]):
                logger.debug(f"Excluding URL (too shallow): {url}")
                return False
        
        return True
    
    async def _extract_program_urls_with_llm(
        self,
        content: str,
        listing_page_url: str,
        base_domain: str
    ) -> List[str]:
        """Use LLM to extract program URLs from content."""
        if not settings.enable_llm_extraction:
            return []
        
        # Truncate content if too long
        if len(content) > 8000:
            content = content[:8000]
        
        prompt = f"""Extract all graduate program URLs from this content. 
A program URL is a link to a specific graduate program page (like "Master of Science in Computer Science" or "PhD in Biology").

Base domain: {base_domain}
Listing page: {listing_page_url}

Return ONLY a JSON array of URLs, nothing else. Example: ["https://example.edu/program/cs", "https://example.edu/program/biology"]

Content:
{content}"""
        
        try:
            if settings.groq_api_key:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.groq_api_key)
                response = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000,
                )
                result = response.choices[0].message.content.strip()
            elif settings.openai_api_key:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000,
                )
                result = response.choices[0].message.content.strip()
            else:
                return []
            
            # Parse JSON from response
            import json
            # Clean up response (remove markdown code blocks if present)
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()
            
            urls = json.loads(result)
            if isinstance(urls, list):
                # Filter to same domain
                filtered = []
                for url in urls:
                    if isinstance(url, str):
                        url_parsed = urlparse(url)
                        url_domain = self._get_base_domain(url_parsed.netloc)
                        if url_domain == base_domain:
                            filtered.append(url)
                logger.info(f"LLM extracted {len(filtered)} program URLs")
                return filtered
        except Exception as e:
            logger.warning(f"LLM program URL extraction failed: {e}")
        
        return []
    
    async def _discover_with_firecrawl(self, base_url: str) -> List[str]:
        """Discover programs using Firecrawl crawl."""
        if not self.firecrawl.is_available():
            return []
        
        try:
            # Crawl with path filters for program pages
            include_paths = [
                "/program/*",
                "/graduate/*",
                "/degree/*",
                "/masters/*",
                "/phd/*",
            ]
            
            pages = self.firecrawl.crawl_site(
                base_url,
                limit=50,
                include_paths=include_paths
            )
            
            program_urls = []
            for page in pages:
                url = page.get("url", "")
                if url and self._is_program_url(url, ""):
                    program_urls.append(url)
            
            return program_urls
        except Exception as e:
            logger.warning(f"Firecrawl discovery failed: {e}")
            return []
    
    async def _discover_with_google(self, institution_name: str, institution_url: str) -> List[str]:
        """Discover programs using Google search."""
        try:
            # Search for graduate programs at the institution
            base_url_parsed = urlparse(institution_url)
            base_domain = self._get_base_domain(base_url_parsed.netloc)
            query = f'"{institution_name}" graduate programs site:{base_domain}'
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            result = await self.nav_tool.run(search_url)
            if not result.get("success"):
                return []
            
            html = result["html"]
            links = self.link_tool.run(html, search_url)
            
            program_urls = []
            
            for link in links:
                url = link["url"]
                url_parsed = urlparse(url)
                url_domain = self._get_base_domain(url_parsed.netloc)
                
                # Must be from same base domain (allow subdomains)
                if url_domain != base_domain:
                    continue
                
                if self._is_program_url(url, link["text"]):
                    program_urls.append(url)
            
            return program_urls
        except Exception as e:
            logger.warning(f"Google discovery failed: {e}")
            return []
    
    def _deduplicate_urls(self, urls: List[str], base_url: str) -> List[str]:
        """Deduplicate and validate URLs."""
        seen = set()
        unique_urls = []
        base_url_parsed = urlparse(base_url)
        base_domain = self._get_base_domain(base_url_parsed.netloc)
        
        for url in urls:
            if not url or not url.startswith("http"):
                continue
            
            url_parsed = urlparse(url)
            url_domain = self._get_base_domain(url_parsed.netloc)
            
            # Must be from same base domain (allow subdomains)
            if url_domain != base_domain:
                continue
            
            # Normalize URL (remove fragments, query params for deduplication)
            normalized = f"{url_parsed.scheme}://{url_parsed.netloc}{url_parsed.path}"
            
            if normalized not in seen:
                seen.add(normalized)
                unique_urls.append(url)  # Keep original URL with params
        
        return unique_urls
    
    async def close(self):
        """Clean up resources."""
        await self.google_agent.close()
        await self.school_agent.close()
        await self.nav_tool.close()

