"""Playwright scraper for dynamic content and JavaScript-rendered pages."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install")


class PlaywrightScraper:
    """Handle dynamic content, JavaScript-rendered pages, and complex interactions."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.browser_type = getattr(settings, "playwright_browser", "headless") or "headless"
        self.timeout = getattr(settings, "playwright_timeout", 30000) or 30000
    
    async def _ensure_browser(self) -> Browser:
        """Ensure browser is initialized."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed")
        
        if self.browser is None:
            playwright = await async_playwright().start()
            if self.browser_type == "chromium":
                self.browser = await playwright.chromium.launch(headless=True)
            elif self.browser_type == "firefox":
                self.browser = await playwright.firefox.launch(headless=True)
            else:
                self.browser = await playwright.chromium.launch(headless=True)
        
        return self.browser
    
    async def scrape_dynamic_page(self, url: str) -> Dict[str, Any]:
        """
        Scrape JavaScript-rendered page.
        
        Args:
            url: URL to scrape
            
        Returns:
            Extracted data dictionary
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning empty data")
            return {}
        
        try:
            browser = await self._ensure_browser()
            page = await browser.new_page()
            
            # Set timeout
            page.set_default_timeout(self.timeout)
            
            # Navigate to page
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            # Wait for content to load
            await page.wait_for_load_state("domcontentloaded")
            
            # Extract content
            data: Dict[str, Any] = {}
            
            # Get page title
            title = await page.title()
            data["name"] = title
            
            # Get main content
            content = await page.content()
            
            # Try to extract structured data
            data.update(await self._extract_structured_data(page))
            
            # Extract text content
            text_content = await page.evaluate("() => document.body.innerText")
            data["text_content"] = text_content[:5000]  # Limit length
            
            await page.close()
            
            return data
            
        except PlaywrightTimeout:
            logger.warning(f"Timeout scraping {url}")
            return {}
        except Exception as e:
            logger.error(f"Error scraping {url} with Playwright: {e}")
            return {}
    
    async def extract_from_tabs(self, page: Page, tab_selectors: List[str]) -> Dict[str, Any]:
        """
        Click through tabs and extract content.
        
        Args:
            page: Playwright page object
            tab_selectors: List of CSS selectors for tabs to click
            
        Returns:
            Dictionary with content from each tab
        """
        tab_data: Dict[str, Any] = {}
        
        for selector in tab_selectors:
            try:
                # Click tab
                await page.click(selector, timeout=5000)
                await page.wait_for_timeout(500)  # Wait for content to load
                
                # Extract content from active tab
                content = await page.evaluate("() => document.body.innerText")
                tab_name = await page.evaluate(f"() => document.querySelector('{selector}')?.textContent")
                
                if tab_name:
                    tab_data[tab_name.strip()] = content[:2000]
                    
            except Exception as e:
                logger.debug(f"Failed to extract from tab {selector}: {e}")
        
        return tab_data
    
    async def handle_infinite_scroll(
        self,
        page: Page,
        max_scrolls: int = 5,
        scroll_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scroll and collect dynamically loaded content.
        
        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scrolls
            scroll_selector: Optional selector for scrollable container
            
        Returns:
            List of extracted items
        """
        items: List[Dict[str, Any]] = []
        previous_height = 0
        
        for i in range(max_scrolls):
            # Scroll to bottom
            if scroll_selector:
                await page.evaluate(f"document.querySelector('{scroll_selector}').scrollTop = document.querySelector('{scroll_selector}').scrollHeight")
            else:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new content
            await page.wait_for_timeout(1000)
            
            # Check if new content loaded
            current_height = await page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                break  # No more content
            
            previous_height = current_height
            
            # Extract items (this would be customized based on page structure)
            # For now, just collect all links
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    url: a.href,
                    text: a.textContent.trim()
                }))
            """)
            
            items.extend(links)
        
        return items
    
    async def _extract_structured_data(self, page: Page) -> Dict[str, Any]:
        """Extract structured data from page using common patterns."""
        data: Dict[str, Any] = {}
        
        try:
            # Extract title
            title = await page.query_selector("h1")
            if title:
                data["name"] = await title.inner_text()
            
            # Extract description (meta or first paragraph)
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                data["description"] = await meta_desc.get_attribute("content")
            else:
                # Try first paragraph
                paragraph = await page.query_selector("p")
                if paragraph:
                    text = await paragraph.inner_text()
                    if len(text) > 50:
                        data["description"] = text[:500]
            
            # Extract deadlines (look for date patterns)
            page_text = await page.evaluate("() => document.body.innerText")
            import re
            deadline_match = re.search(
                r"(?:deadline|due date)[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
                page_text,
                re.IGNORECASE
            )
            if deadline_match:
                data["application_deadline_primary"] = deadline_match.group(1)
            
            # Extract tuition
            tuition_match = re.search(
                r"\$([\d,]+(?:\.\d{2})?)\s*(?:per\s+)?(?:year|annually)",
                page_text,
                re.IGNORECASE
            )
            if tuition_match:
                try:
                    amount_str = tuition_match.group(1).replace(",", "")
                    data["tuition_estimate_per_year"] = float(amount_str)
                except ValueError:
                    pass
            
        except Exception as e:
            logger.debug(f"Error extracting structured data: {e}")
        
        return data
    
    async def close(self):
        """Close browser and clean up resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None

