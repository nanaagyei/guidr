"""LLM-powered program navigation agent for extracting program data."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.config import settings
from src.scrapers.agents.tools import WebNavigationTool, HTMLParserTool
from src.services.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


class ProgramNavigationAgent:
    """Intelligent agent that navigates program pages and extracts information."""
    
    def __init__(self):
        self.nav_tool = WebNavigationTool()
        self.parser_tool = HTMLParserTool()
        self.llm_extractor = LLMExtractor()
    
    async def navigate_and_extract(self, program_url: str) -> Dict[str, Any]:
        """
        LLM agent navigates page and extracts structured data.
        
        Args:
            program_url: URL of the program page
            
        Returns:
            Extracted program data dictionary
        """
        try:
            # Navigate to page
            result = await self.nav_tool.run(program_url)
            if not result.get("success"):
                logger.warning(f"Failed to navigate to {program_url}")
                return {}
            
            html = result["html"]
            
            # Extract structured data using LLM
            if settings.enable_llm_extraction:
                extracted = await self.llm_extractor.extract_program_data(html, program_url)
                if extracted:
                    return extracted
            
            # Fallback: extract sections manually
            return await self._extract_sections_manual(html, program_url)
            
        except Exception as e:
            logger.error(f"Error navigating and extracting from {program_url}: {e}")
            return {}
    
    async def extract_section(self, html: str, section_name: str) -> Optional[str]:
        """
        Extract specific section content using LLM.
        
        Args:
            html: HTML content
            section_name: Name of section to extract (e.g., "admissions requirements")
            
        Returns:
            Extracted section content or None
        """
        if not settings.enable_llm_extraction:
            return None
        
        # Truncate HTML if too long
        if len(html) > 10000:
            html = html[:10000]
        
        prompt = f"""Extract the "{section_name}" section from this HTML content. Return only the relevant text content, nothing else.

HTML:
{html}"""
        
        try:
            if settings.groq_api_key:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.groq_api_key)
                response = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
            elif settings.openai_api_key:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"LLM section extraction failed: {e}")
        
        return None
    
    async def _extract_sections_manual(self, html: str, url: str) -> Dict[str, Any]:
        """Manually extract sections from HTML as fallback."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        data: Dict[str, Any] = {}
        
        # Extract title
        title = soup.find("h1")
        if title:
            data["name"] = title.get_text(strip=True)
        
        # Extract description (first substantial paragraph or meta description)
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            data["description"] = meta_desc["content"]
        else:
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 100:
                    data["description"] = text[:1000]
                    break
        
        # Try to find common sections
        section_keywords = {
            "admissions requirements": ["admission", "requirement", "apply"],
            "deadlines": ["deadline", "due date", "application date"],
            "tuition": ["tuition", "cost", "fee", "price"],
            "funding": ["funding", "scholarship", "assistantship", "fellowship"],
        }
        
        # Look for sections with these keywords
        for section_name, keywords in section_keywords.items():
            section_content = self._find_section_by_keywords(soup, keywords)
            if section_content:
                data[section_name] = section_content
        
        return data
    
    def _find_section_by_keywords(self, soup, keywords: list) -> Optional[str]:
        """Find a section containing any of the keywords."""
        # Look for headings containing keywords
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            heading_text = heading.get_text(strip=True).lower()
            if any(keyword in heading_text for keyword in keywords):
                # Get content after this heading
                content_parts = []
                for sibling in heading.next_siblings:
                    if sibling.name in ["h1", "h2", "h3", "h4"]:
                        break
                    if hasattr(sibling, "get_text"):
                        text = sibling.get_text(strip=True)
                        if text:
                            content_parts.append(text)
                
                if content_parts:
                    return " ".join(content_parts[:3])  # First 3 paragraphs
        
        return None
    
    async def close(self):
        """Clean up resources."""
        await self.nav_tool.close()

