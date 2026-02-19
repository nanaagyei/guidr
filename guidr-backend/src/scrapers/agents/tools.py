"""LangChain tools for web scraping and data extraction."""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from src.config import settings


class WebNavigationTool:
    """Tool for navigating to web pages and fetching HTML content."""
    
    name = "navigate_webpage"
    description = "Navigate to a URL and retrieve the HTML content. Use this to fetch web pages."
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": settings.scraper_user_agent},
                follow_redirects=True,
            )
        return self._client
    
    async def run(self, url: str) -> Dict[str, Any]:
        """Fetch HTML content from URL."""
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "html": response.text,
                "content_type": response.headers.get("content-type", ""),
            }
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_msg = str(e)
            
            # Provide more helpful error messages
            if status_code == 403:
                error_msg = (
                    f"Access forbidden (403). The site may be blocking scrapers. "
                    f"Consider checking robots.txt or using alternative methods."
                )
            elif status_code == 429:
                error_msg = (
                    f"Rate limited (429). Too many requests. "
                    f"Consider adding delays between requests."
                )
            elif status_code == 404:
                error_msg = f"Page not found (404). The URL may be incorrect or the page may have been removed."
            
            return {
                "success": False,
                "error": error_msg,
                "url": url,
                "status_code": status_code,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


class LinkExtractorTool:
    """Tool for extracting links from HTML content."""
    
    name = "extract_links"
    description = "Extract all links from HTML content. Useful for finding program pages."
    
    def run(self, html: str, base_url: str, pattern: Optional[str] = None) -> List[Dict[str, str]]:
        """Extract links matching optional pattern."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            text = anchor.get_text(strip=True)
            
            # Make absolute URL
            full_url = urljoin(base_url, href)
            
            # Skip non-http links
            if not full_url.startswith(("http://", "https://")):
                continue
            
            # Optional pattern filter
            if pattern and not re.search(pattern, full_url, re.IGNORECASE):
                continue
            
            links.append({
                "url": full_url,
                "text": text[:200],  # Truncate long text
            })
        
        return links


class HTMLParserTool:
    """Tool for parsing structured data from HTML."""
    
    name = "parse_html"
    description = "Parse structured data from HTML using CSS selectors."
    
    def run(
        self, 
        html: str, 
        selectors: Dict[str, str],
        list_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse HTML using CSS selectors.
        
        Args:
            html: HTML content
            selectors: Dict mapping field names to CSS selectors
            list_selector: If provided, find all matching elements
            
        Returns:
            Extracted data
        """
        soup = BeautifulSoup(html, "html.parser")
        
        if list_selector:
            # Extract list of items
            items = []
            for element in soup.select(list_selector):
                item = {}
                for field, selector in selectors.items():
                    found = element.select_one(selector)
                    item[field] = found.get_text(strip=True) if found else None
                items.append(item)
            return {"items": items}
        
        # Extract single values
        result = {}
        for field, selector in selectors.items():
            found = soup.select_one(selector)
            result[field] = found.get_text(strip=True) if found else None
        
        return result


class ProgramDataExtractorTool:
    """Tool specifically for extracting graduate program data."""
    
    name = "extract_program_data"
    description = "Extract graduate program information from HTML content."
    
    # Common patterns for program data
    DEADLINE_PATTERNS = [
        r"deadline[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        r"due[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        r"applications?\s+(?:due|deadline)[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
    ]
    
    TUITION_PATTERNS = [
        r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:per\s+)?(?:year|semester|credit))?",
        r"tuition[:\s]*\$[\d,]+",
    ]
    
    GRE_PATTERNS = [
        r"GRE\s+(?:required|optional|not\s+required|waived)",
        r"(?:minimum|average)\s+GRE[:\s]*\d+",
    ]
    
    def run(self, html: str, url: str) -> Dict[str, Any]:
        """Extract program data from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        
        # Extract title
        title = None
        for tag in ["h1", "title"]:
            elem = soup.find(tag)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Extract description
        description = None
        for selector in ["meta[name='description']", "meta[property='og:description']"]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                description = meta["content"]
                break
        
        if not description:
            # Try to get first substantial paragraph
            for p in soup.find_all("p"):
                p_text = p.get_text(strip=True)
                if len(p_text) > 100:
                    description = p_text[:500]
                    break
        
        # Extract deadlines
        deadlines = []
        for pattern in self.DEADLINE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            deadlines.extend(matches)
        
        # Extract tuition
        tuition_matches = []
        for pattern in self.TUITION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tuition_matches.extend(matches)
        
        # Extract GRE requirements
        gre_info = None
        for pattern in self.GRE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                gre_info = match.group(0)
                break
        
        # Detect degree level
        degree_level = None
        text_lower = text.lower()
        if "ph.d" in text_lower or "phd" in text_lower or "doctorate" in text_lower:
            degree_level = "phd"
        elif "master" in text_lower or "m.s." in text_lower or "m.a." in text_lower:
            degree_level = "masters"
        
        # Extract field of study from URL or title
        field_of_study = self._extract_field(url, title)
        
        return {
            "name": title,
            "degree_level": degree_level,
            "field_of_study": field_of_study,
            "description": description,
            "deadlines": deadlines[:3] if deadlines else None,
            "tuition_info": tuition_matches[:2] if tuition_matches else None,
            "gre_requirement": gre_info,
            "source_url": url,
        }
    
    def _extract_field(self, url: str, title: Optional[str]) -> Optional[str]:
        """Try to extract field of study."""
        # Common fields
        fields = [
            "computer science", "biology", "chemistry", "physics",
            "mathematics", "engineering", "psychology", "economics",
            "business", "data science", "machine learning", "artificial intelligence",
            "neuroscience", "biotechnology", "environmental science",
        ]
        
        search_text = f"{url} {title or ''}".lower()
        for field in fields:
            if field in search_text:
                return field.title()
        
        return None


class TableExtractorTool:
    """Tool for extracting data from HTML tables."""
    
    name = "extract_table"
    description = "Extract data from HTML tables into structured format."
    
    def run(self, html: str, table_index: int = 0) -> List[Dict[str, str]]:
        """Extract table data."""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        
        if not tables or table_index >= len(tables):
            return []
        
        table = tables[table_index]
        rows = []
        headers = []
        
        # Get headers
        header_row = table.find("thead")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        else:
            # Try first row
            first_row = table.find("tr")
            if first_row:
                headers = [cell.get_text(strip=True) for cell in first_row.find_all(["th", "td"])]
        
        # Get data rows
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells and cells != headers:  # Skip header row
                if headers:
                    row = dict(zip(headers, cells))
                else:
                    row = {f"col_{i}": c for i, c in enumerate(cells)}
                rows.append(row)
        
        return rows


# Export all tools
AVAILABLE_TOOLS = [
    WebNavigationTool,
    LinkExtractorTool,
    HTMLParserTool,
    ProgramDataExtractorTool,
    TableExtractorTool,
]

