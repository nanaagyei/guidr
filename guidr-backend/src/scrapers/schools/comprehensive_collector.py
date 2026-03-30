"""Comprehensive school data collector using multiple methods."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from src.config import settings
from src.scrapers.schools.firecrawl_scraper import FirecrawlScraper
from src.scrapers.schools.scorecard import CollegeScorecardClient
from src.scrapers.agents.google_search_agent import GoogleSearchAgent
from src.scrapers.agents.school_scraper_agent import SchoolScraperAgent
from src.services.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


class ComprehensiveSchoolCollector:
    """Collects comprehensive school data using multiple methods."""
    
    def __init__(self):
        self.firecrawl = FirecrawlScraper()
        self.scorecard = CollegeScorecardClient()
        self.google_agent = GoogleSearchAgent()
        self.school_agent = SchoolScraperAgent()
        self.llm_extractor = LLMExtractor()
    
    async def collect_school_data(self, institution_name: str, website_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect comprehensive school data using all available methods.
        
        Args:
            institution_name: Name of the institution
            website_url: Optional website URL (will search if not provided)
            
        Returns:
            Dictionary with collected school data
        """
        data: Dict[str, Any] = {
            "name": institution_name,
            "website_url": website_url,
            "description": None,
            "acceptance_rate": None,
            "tuition": {},
            "funding_opportunities": [],
            "rankings": {},
            "program_count": None,
        }
        
        # 1. Find website if not provided
        if not website_url:
            logger.info(f"Searching for website for {institution_name}")
            website_url = await self.google_agent.find_school_website(institution_name)
            data["website_url"] = website_url
        
        if not website_url:
            logger.warning(f"Could not find website for {institution_name}")
            return data
        
        # 2. Collect description using Firecrawl + LLM
        logger.info(f"Collecting description for {institution_name}")
        description = await self.extract_description(website_url)
        if description:
            data["description"] = description
        
        # 3. Collect acceptance rate
        logger.info(f"Collecting acceptance rate for {institution_name}")
        acceptance_rate = await self.extract_acceptance_rate(website_url)
        if acceptance_rate:
            data["acceptance_rate"] = acceptance_rate
        
        # 4. Collect tuition information
        logger.info(f"Collecting tuition for {institution_name}")
        tuition_data = await self.extract_tuition(website_url)
        if tuition_data:
            data["tuition"] = tuition_data
        
        # 5. Collect funding opportunities
        logger.info(f"Collecting funding info for {institution_name}")
        funding_info = await self.extract_funding_info(website_url)
        if funding_info:
            data["funding_opportunities"] = funding_info
        
        # 6. Get financial data from College Scorecard (for US schools)
        if institution_name and "USA" in str(data.get("country", "")):
            logger.info(f"Enriching with College Scorecard data for {institution_name}")
            scorecard_data = await self._get_scorecard_data(institution_name)
            if scorecard_data:
                # Merge tuition data
                if scorecard_data.get("in_state_tuition"):
                    data["tuition"]["in_state"] = scorecard_data["in_state_tuition"]
                if scorecard_data.get("out_of_state_tuition"):
                    data["tuition"]["out_of_state"] = scorecard_data["out_of_state_tuition"]
                if scorecard_data.get("average_cost"):
                    data["tuition"]["average_cost"] = scorecard_data["average_cost"]
        
        return data
    
    async def extract_description(self, url: str) -> Optional[str]:
        """Extract comprehensive school description using Firecrawl + LLM."""
        # Try Firecrawl first
        if self.firecrawl.is_available():
            try:
                result = self.firecrawl.scrape_url(url, formats=["markdown"])
                if result and result.get("markdown"):
                    markdown = result["markdown"]
                    # Use LLM to extract a concise description
                    if settings.enable_llm_extraction:
                        description = await self._llm_extract_description(markdown)
                        if description:
                            return description
                    # Fallback: use first paragraph
                    paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
                    if paragraphs:
                        return paragraphs[0][:1000]  # Limit length
            except Exception as e:
                logger.warning(f"Firecrawl extraction failed for {url}: {e}")
        
        # Fallback: use school agent
        try:
            result = await self.school_agent.nav_tool.run(url)
            if result.get("success"):
                html = result["html"]
                if settings.enable_llm_extraction:
                    description = await self._llm_extract_description(html)
                    if description:
                        return description
        except Exception as e:
            logger.warning(f"Description extraction failed for {url}: {e}")
        
        return None
    
    async def _llm_extract_description(self, content: str) -> Optional[str]:
        """Use LLM to extract a concise school description."""
        # Truncate content if too long
        if len(content) > 5000:
            content = content[:5000]
        
        prompt = f"""Extract a comprehensive 2-3 paragraph description of this university/school from the following content. Focus on:
- Mission and values
- Academic strengths
- Notable programs or research areas
- Campus culture or location highlights

Content:
{content}

Return only the description, nothing else."""
        
        try:
            if settings.groq_api_key:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.groq_api_key)
                response = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
            elif settings.openai_api_key:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"LLM description extraction failed: {e}")
        
        return None
    
    async def extract_acceptance_rate(self, website_url: str) -> Optional[float]:
        """Extract acceptance rate from admissions pages."""
        # Try to find admissions page
        admissions_urls = [
            urljoin(website_url, "/admissions"),
            urljoin(website_url, "/admission"),
            urljoin(website_url, "/apply"),
            urljoin(website_url, "/graduate-admissions"),
        ]
        
        for url in admissions_urls:
            try:
                result = await self.school_agent.nav_tool.run(url)
                if result.get("success"):
                    html = result["html"]
                    # Look for acceptance rate patterns
                    rate = self._parse_acceptance_rate(html)
                    if rate:
                        return rate
            except Exception as e:
                logger.debug(f"Failed to check {url}: {e}")
        
        # Try Firecrawl
        if self.firecrawl.is_available():
            for url in admissions_urls[:2]:  # Limit to first 2
                try:
                    result = self.firecrawl.scrape_url(url, formats=["markdown"])
                    if result and result.get("markdown"):
                        rate = self._parse_acceptance_rate(result["markdown"])
                        if rate:
                            return rate
                except Exception as e:
                    logger.debug(f"Firecrawl failed for {url}: {e}")
        
        return None
    
    def _parse_acceptance_rate(self, text: str) -> Optional[float]:
        """Parse acceptance rate from text."""
        # Common patterns
        patterns = [
            r"acceptance\s+rate[:\s]*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s*acceptance",
            r"accepts?\s+(\d+(?:\.\d+)?)\s*%",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    rate = float(match.group(1))
                    if 0 <= rate <= 100:
                        return rate
                except ValueError:
                    continue
        
        return None
    
    async def extract_tuition(self, website_url: str) -> Dict[str, Any]:
        """Extract tuition information from website."""
        tuition_data: Dict[str, Any] = {}
        
        # Try to find tuition/financial aid page
        tuition_urls = [
            urljoin(website_url, "/tuition"),
            urljoin(website_url, "/cost"),
            urljoin(website_url, "/financial-aid"),
            urljoin(website_url, "/fees"),
        ]
        
        for url in tuition_urls:
            try:
                result = await self.school_agent.nav_tool.run(url)
                if result.get("success"):
                    html = result["html"]
                    parsed = self._parse_tuition(html)
                    if parsed:
                        tuition_data.update(parsed)
                        break
            except Exception as e:
                logger.debug(f"Failed to check {url}: {e}")
        
        return tuition_data
    
    def _parse_tuition(self, html: str) -> Dict[str, float]:
        """Parse tuition amounts from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        
        tuition_data: Dict[str, float] = {}
        
        # Patterns for different tuition types
        patterns = {
            "in_state": [
                r"in[- ]state[:\s]*\$?([\d,]+(?:\.\d{2})?)",
                r"resident[:\s]*\$?([\d,]+(?:\.\d{2})?)",
            ],
            "out_of_state": [
                r"out[- ]of[- ]state[:\s]*\$?([\d,]+(?:\.\d{2})?)",
                r"non[- ]resident[:\s]*\$?([\d,]+(?:\.\d{2})?)",
            ],
            "total": [
                r"tuition[:\s]*\$?([\d,]+(?:\.\d{2})?)",
                r"total\s+cost[:\s]*\$?([\d,]+(?:\.\d{2})?)",
            ],
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(",", "")
                        amount = float(amount_str)
                        if amount > 0:
                            tuition_data[key] = amount
                            break
                    except (ValueError, AttributeError):
                        continue
        
        return tuition_data
    
    async def extract_funding_info(self, website_url: str) -> List[str]:
        """Extract funding opportunities, scholarships, assistantships."""
        funding_info: List[str] = []
        
        # Try to find funding/financial aid page
        funding_urls = [
            urljoin(website_url, "/financial-aid"),
            urljoin(website_url, "/funding"),
            urljoin(website_url, "/scholarships"),
            urljoin(website_url, "/assistantships"),
            urljoin(website_url, "/graduate-funding"),
        ]
        
        for url in funding_urls:
            try:
                result = await self.school_agent.nav_tool.run(url)
                if result.get("success"):
                    html = result["html"]
                    # Extract funding opportunities
                    opportunities = self._parse_funding_opportunities(html)
                    funding_info.extend(opportunities)
            except Exception as e:
                logger.debug(f"Failed to check {url}: {e}")
        
        return list(set(funding_info))  # Deduplicate
    
    def _parse_funding_opportunities(self, html: str) -> List[str]:
        """Parse funding opportunities from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        
        opportunities: List[str] = []
        
        # Look for common funding types
        funding_keywords = [
            "scholarship",
            "fellowship",
            "assistantship",
            "grant",
            "stipend",
            "tuition waiver",
            "research funding",
        ]
        
        # Extract sentences containing funding keywords
        sentences = re.split(r"[.!?]\s+", text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in funding_keywords:
                if keyword in sentence_lower and len(sentence.strip()) > 20:
                    opportunities.append(sentence.strip()[:200])  # Limit length
                    break
        
        return opportunities[:10]  # Limit to 10
    
    async def _get_scorecard_data(self, institution_name: str) -> Optional[Dict[str, Any]]:
        """Get financial data from College Scorecard API."""
        # This would require matching institution name to IPEDS unit ID
        # For now, return None - can be enhanced later
        return None
    
    async def close(self):
        """Clean up resources."""
        await self.google_agent.close()
        await self.school_agent.close()

