"""Firecrawl-based scraper for top graduate schools and programs.

Uses Firecrawl API for intelligent web scraping with:
- Curated list of top US and international graduate schools
- LLM-powered content extraction
- Graduate program discovery
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx
import json

from src.config import settings
from src.scrapers.base import InstitutionSeed

logger = logging.getLogger(__name__)


# Curated list of top graduate schools with their program pages
TOP_GRADUATE_SCHOOLS = [
    # Top US Universities
    {
        "name": "Massachusetts Institute of Technology",
        "short_name": "MIT",
        "website_url": "https://www.mit.edu",
        "grad_programs_url": "https://gradadmissions.mit.edu/programs",
        "country": "USA",
        "state_or_province": "MA",
        "city": "Cambridge",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Stanford University",
        "website_url": "https://www.stanford.edu",
        "grad_programs_url": "https://gradadmissions.stanford.edu/programs",
        "country": "USA",
        "state_or_province": "CA",
        "city": "Stanford",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Harvard University",
        "website_url": "https://www.harvard.edu",
        "grad_programs_url": "https://gsas.harvard.edu/programs-of-study",
        "country": "USA",
        "state_or_province": "MA",
        "city": "Cambridge",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "California Institute of Technology",
        "short_name": "Caltech",
        "website_url": "https://www.caltech.edu",
        "grad_programs_url": "https://www.caltech.edu/academics/graduate-studies",
        "country": "USA",
        "state_or_province": "CA",
        "city": "Pasadena",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "University of California, Berkeley",
        "short_name": "UC Berkeley",
        "website_url": "https://www.berkeley.edu",
        "grad_programs_url": "https://grad.berkeley.edu/programs/",
        "country": "USA",
        "state_or_province": "CA",
        "city": "Berkeley",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "Princeton University",
        "website_url": "https://www.princeton.edu",
        "grad_programs_url": "https://gradschool.princeton.edu/academics/degrees-requirements",
        "country": "USA",
        "state_or_province": "NJ",
        "city": "Princeton",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Columbia University",
        "website_url": "https://www.columbia.edu",
        "grad_programs_url": "https://gsas.columbia.edu/degree-programs",
        "country": "USA",
        "state_or_province": "NY",
        "city": "New York",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "University of Chicago",
        "website_url": "https://www.uchicago.edu",
        "grad_programs_url": "https://grad.uchicago.edu/academic-programs/",
        "country": "USA",
        "state_or_province": "IL",
        "city": "Chicago",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Yale University",
        "website_url": "https://www.yale.edu",
        "grad_programs_url": "https://gsas.yale.edu/academics/departments-programs",
        "country": "USA",
        "state_or_province": "CT",
        "city": "New Haven",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "University of Pennsylvania",
        "short_name": "Penn",
        "website_url": "https://www.upenn.edu",
        "grad_programs_url": "https://www.upenn.edu/graduate",
        "country": "USA",
        "state_or_province": "PA",
        "city": "Philadelphia",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Cornell University",
        "website_url": "https://www.cornell.edu",
        "grad_programs_url": "https://gradschool.cornell.edu/academics/fields-of-study/",
        "country": "USA",
        "state_or_province": "NY",
        "city": "Ithaca",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Duke University",
        "website_url": "https://www.duke.edu",
        "grad_programs_url": "https://gradschool.duke.edu/academics/programs/",
        "country": "USA",
        "state_or_province": "NC",
        "city": "Durham",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Northwestern University",
        "website_url": "https://www.northwestern.edu",
        "grad_programs_url": "https://www.tgs.northwestern.edu/academics/programs/",
        "country": "USA",
        "state_or_province": "IL",
        "city": "Evanston",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Johns Hopkins University",
        "website_url": "https://www.jhu.edu",
        "grad_programs_url": "https://krieger.jhu.edu/graduate-admissions/programs/",
        "country": "USA",
        "state_or_province": "MD",
        "city": "Baltimore",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "University of Michigan",
        "website_url": "https://umich.edu",
        "grad_programs_url": "https://rackham.umich.edu/programs/",
        "country": "USA",
        "state_or_province": "MI",
        "city": "Ann Arbor",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "Carnegie Mellon University",
        "short_name": "CMU",
        "website_url": "https://www.cmu.edu",
        "grad_programs_url": "https://www.cmu.edu/academics/graduate-programs.html",
        "country": "USA",
        "state_or_province": "PA",
        "city": "Pittsburgh",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "University of California, Los Angeles",
        "short_name": "UCLA",
        "website_url": "https://www.ucla.edu",
        "grad_programs_url": "https://grad.ucla.edu/programs/",
        "country": "USA",
        "state_or_province": "CA",
        "city": "Los Angeles",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "New York University",
        "short_name": "NYU",
        "website_url": "https://www.nyu.edu",
        "grad_programs_url": "https://gsas.nyu.edu/programs.html",
        "country": "USA",
        "state_or_province": "NY",
        "city": "New York",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Georgia Institute of Technology",
        "short_name": "Georgia Tech",
        "website_url": "https://www.gatech.edu",
        "grad_programs_url": "https://grad.gatech.edu/degree-programs",
        "country": "USA",
        "state_or_province": "GA",
        "city": "Atlanta",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Texas at Austin",
        "short_name": "UT Austin",
        "website_url": "https://www.utexas.edu",
        "grad_programs_url": "https://gradschool.utexas.edu/academics/programs",
        "country": "USA",
        "state_or_province": "TX",
        "city": "Austin",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Washington",
        "short_name": "UW",
        "website_url": "https://www.washington.edu",
        "grad_programs_url": "https://grad.uw.edu/graduate-programs/",
        "country": "USA",
        "state_or_province": "WA",
        "city": "Seattle",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Illinois Urbana-Champaign",
        "short_name": "UIUC",
        "website_url": "https://illinois.edu",
        "grad_programs_url": "https://grad.illinois.edu/catalog/programs",
        "country": "USA",
        "state_or_province": "IL",
        "city": "Urbana",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Wisconsin-Madison",
        "website_url": "https://www.wisc.edu",
        "grad_programs_url": "https://grad.wisc.edu/programs/",
        "country": "USA",
        "state_or_province": "WI",
        "city": "Madison",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Southern California",
        "short_name": "USC",
        "website_url": "https://www.usc.edu",
        "grad_programs_url": "https://graduateschool.usc.edu/degrees-and-programs/",
        "country": "USA",
        "state_or_province": "CA",
        "city": "Los Angeles",
        "public_private": "private",
        "institution_type": "university",
    },
    {
        "name": "Boston University",
        "short_name": "BU",
        "website_url": "https://www.bu.edu",
        "grad_programs_url": "https://www.bu.edu/grad/programs-admissions/programs/",
        "country": "USA",
        "state_or_province": "MA",
        "city": "Boston",
        "public_private": "private",
        "institution_type": "university",
    },
    # Top International Universities
    {
        "name": "University of Oxford",
        "website_url": "https://www.ox.ac.uk",
        "grad_programs_url": "https://www.ox.ac.uk/admissions/graduate/courses/",
        "country": "United Kingdom",
        "city": "Oxford",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Cambridge",
        "website_url": "https://www.cam.ac.uk",
        "grad_programs_url": "https://www.postgraduate.study.cam.ac.uk/courses",
        "country": "United Kingdom",
        "city": "Cambridge",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "Imperial College London",
        "website_url": "https://www.imperial.ac.uk",
        "grad_programs_url": "https://www.imperial.ac.uk/study/pg/courses/",
        "country": "United Kingdom",
        "city": "London",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "ETH Zurich",
        "website_url": "https://ethz.ch",
        "grad_programs_url": "https://ethz.ch/en/studies/master.html",
        "country": "Switzerland",
        "city": "Zurich",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Toronto",
        "website_url": "https://www.utoronto.ca",
        "grad_programs_url": "https://www.sgs.utoronto.ca/programs/",
        "country": "Canada",
        "state_or_province": "ON",
        "city": "Toronto",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "McGill University",
        "website_url": "https://www.mcgill.ca",
        "grad_programs_url": "https://www.mcgill.ca/gradapplicants/programs",
        "country": "Canada",
        "state_or_province": "QC",
        "city": "Montreal",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of British Columbia",
        "short_name": "UBC",
        "website_url": "https://www.ubc.ca",
        "grad_programs_url": "https://www.grad.ubc.ca/prospective-students/graduate-degree-programs",
        "country": "Canada",
        "state_or_province": "BC",
        "city": "Vancouver",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "National University of Singapore",
        "short_name": "NUS",
        "website_url": "https://www.nus.edu.sg",
        "grad_programs_url": "https://www.nus.edu.sg/registrar/academic-information-policies/graduate",
        "country": "Singapore",
        "city": "Singapore",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Melbourne",
        "website_url": "https://www.unimelb.edu.au",
        "grad_programs_url": "https://study.unimelb.edu.au/find/graduate-research/",
        "country": "Australia",
        "city": "Melbourne",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "University of Sydney",
        "website_url": "https://www.sydney.edu.au",
        "grad_programs_url": "https://www.sydney.edu.au/courses/courses/search.html?search-type=course&course-level=postgraduate",
        "country": "Australia",
        "city": "Sydney",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "Technical University of Munich",
        "short_name": "TUM",
        "website_url": "https://www.tum.de",
        "grad_programs_url": "https://www.tum.de/en/studies/degree-programs/masters-programs",
        "country": "Germany",
        "city": "Munich",
        "public_private": "public",
        "institution_type": "university",
    },
    {
        "name": "Ludwig Maximilian University of Munich",
        "short_name": "LMU Munich",
        "website_url": "https://www.lmu.de",
        "grad_programs_url": "https://www.en.uni-muenchen.de/students/degree/master/index.html",
        "country": "Germany",
        "city": "Munich",
        "public_private": "public",
        "institution_type": "university",
    },
]


@dataclass
class ProgramSeed:
    """Seed data for a graduate program."""
    name: str
    institution_name: str
    degree_level: str  # 'masters', 'phd', 'professional'
    field_of_study: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    application_deadline: Optional[str] = None
    tuition_domestic: Optional[float] = None
    tuition_international: Optional[float] = None
    duration_months: Optional[int] = None


class FirecrawlScraper:
    """Scraper using Firecrawl API for intelligent web scraping."""

    FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"
    DEFAULT_DELAY = 1.0  # Default delay between requests (seconds)
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 2.0  # Initial backoff time for exponential backoff

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60, delay: float = None):
        self.api_key = api_key or settings.firecrawl_api_key
        self.timeout = timeout
        self.delay = delay or getattr(settings, 'scraper_delay_seconds', self.DEFAULT_DELAY) or self.DEFAULT_DELAY
        self._client = httpx.Client(timeout=timeout)
        self._last_request_time = 0.0

    def is_available(self) -> bool:
        """Check if Firecrawl is configured."""
        return bool(self.api_key)

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def scrape_url(self, url: str, formats: List[str] = None, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """Scrape a single URL using Firecrawl with rate limiting and retry logic.

        Args:
            url: The URL to scrape
            formats: Output formats - ['markdown', 'html', 'rawHtml', 'links', 'screenshot']
            retry_count: Current retry attempt (for exponential backoff)

        Returns:
            Scraped content dict or None if failed
        """
        if not self.is_available():
            logger.warning("Firecrawl API key not configured")
            return None

        formats = formats or ["markdown", "links"]

        # Rate limiting
        self._rate_limit()

        try:
            response = self._client.post(
                f"{self.FIRECRAWL_API_URL}/scrape",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": formats,
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data.get("data", {})
            else:
                logger.warning("Firecrawl scrape failed for %s: %s", url, data.get("error"))
                return None

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            # Handle rate limiting (429) with exponential backoff
            if status_code == 429 and retry_count < self.MAX_RETRIES:
                backoff_time = self.INITIAL_BACKOFF * (2 ** retry_count)
                logger.warning(
                    "Firecrawl rate limited (429) for %s. Retrying in %s seconds (attempt %d/%d)",
                    url, backoff_time, retry_count + 1, self.MAX_RETRIES
                )
                time.sleep(backoff_time)
                return self.scrape_url(url, formats, retry_count + 1)

            # Handle 403 Forbidden (site blocking)
            elif status_code == 403:
                logger.warning(
                    "Firecrawl blocked (403) for %s. Site may be blocking scrapers. "
                    "Consider using alternative methods or checking robots.txt",
                    url
                )
                return None

            # Handle other HTTP errors
            else:
                logger.error("Firecrawl HTTP error for %s: %s (status: %d)", url, e, status_code)
                return None

        except Exception as e:
            logger.error("Firecrawl error for %s: %s", url, e)
            return None

    def crawl_site(self, url: str, limit: int = 10, include_paths: List[str] = None, retry_count: int = 0) -> List[Dict[str, Any]]:
        """Crawl multiple pages from a website with rate limiting and retry logic.

        Args:
            url: Starting URL
            limit: Maximum pages to crawl
            include_paths: List of path patterns to include (e.g., ['/programs/*'])
            retry_count: Current retry attempt (for exponential backoff)

        Returns:
            List of scraped page data
        """
        if not self.is_available():
            logger.warning("Firecrawl API key not configured")
            return []

        # Rate limiting
        self._rate_limit()

        try:
            payload = {
                "url": url,
                "limit": limit,
                "scrapeOptions": {
                    "formats": ["markdown", "links"],
                },
            }
            if include_paths:
                payload["includePaths"] = include_paths

            response = self._client.post(
                f"{self.FIRECRAWL_API_URL}/crawl",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                # Crawl returns an async job, we need to poll for results
                job_id = data.get("id")
                return self._poll_crawl_job(job_id)
            else:
                logger.warning("Firecrawl crawl failed: %s", data.get("error"))
                return []

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            # Handle rate limiting (429) with exponential backoff
            if status_code == 429 and retry_count < self.MAX_RETRIES:
                backoff_time = self.INITIAL_BACKOFF * (2 ** retry_count)
                logger.warning(
                    "Firecrawl rate limited (429) for crawl %s. Retrying in %s seconds (attempt %d/%d)",
                    url, backoff_time, retry_count + 1, self.MAX_RETRIES
                )
                time.sleep(backoff_time)
                return self.crawl_site(url, limit, include_paths, retry_count + 1)

            # Handle 403 Forbidden
            elif status_code == 403:
                logger.warning(
                    "Firecrawl blocked (403) for crawl %s. Site may be blocking scrapers.",
                    url
                )
                return []

            else:
                logger.error("Firecrawl crawl HTTP error for %s: %s (status: %d)", url, e, status_code)
                return []

        except Exception as e:
            logger.error("Firecrawl crawl error: %s", e)
            return []

    def _poll_crawl_job(self, job_id: str, max_wait: int = 120) -> List[Dict[str, Any]]:
        """Poll for crawl job completion."""
        import time

        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = self._client.get(
                    f"{self.FIRECRAWL_API_URL}/crawl/{job_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                if status == "completed":
                    return data.get("data", [])
                elif status == "failed":
                    logger.error("Crawl job %s failed", job_id)
                    return []

                time.sleep(2)

            except Exception as e:
                logger.error("Error polling crawl job %s: %s", job_id, e)
                return []

        logger.warning("Crawl job %s timed out", job_id)
        return []

    async def crawl_program_pages(
        self,
        base_url: str,
        include_paths: List[str],
        retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Crawl program pages with path filters and rate limiting.

        Args:
            base_url: Base URL of the institution
            include_paths: List of path patterns to include (e.g., ['/programs/*'])
            retry_count: Current retry attempt (for exponential backoff)

        Returns:
            List of scraped page data
        """
        if not self.is_available():
            logger.warning("Firecrawl API key not configured")
            return []

        # Rate limiting
        self._rate_limit()

        try:
            payload = {
                "url": base_url,
                "limit": 50,
                "includePaths": include_paths,
                "scrapeOptions": {
                    "formats": ["markdown", "links"],
                },
            }

            response = self._client.post(
                f"{self.FIRECRAWL_API_URL}/crawl",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                job_id = data.get("id")
                return self._poll_crawl_job(job_id)
            else:
                logger.warning("Firecrawl crawl failed: %s", data.get("error"))
                return []

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            # Handle rate limiting (429) with exponential backoff
            if status_code == 429 and retry_count < self.MAX_RETRIES:
                backoff_time = self.INITIAL_BACKOFF * (2 ** retry_count)
                logger.warning(
                    "Firecrawl rate limited (429) for program crawl %s. Retrying in %s seconds (attempt %d/%d)",
                    base_url, backoff_time, retry_count + 1, self.MAX_RETRIES
                )
                await asyncio.sleep(backoff_time)
                return await self.crawl_program_pages(base_url, include_paths, retry_count + 1)

            # Handle 403 Forbidden
            elif status_code == 403:
                logger.warning(
                    "Firecrawl blocked (403) for program crawl %s. Site may be blocking scrapers.",
                    base_url
                )
                return []

            else:
                logger.error("Firecrawl program crawl HTTP error for %s: %s (status: %d)", base_url, e, status_code)
                return []

        except Exception as e:
            logger.error("Firecrawl crawl error: %s", e)
            return []

    async def extract_programs_structured(
        self,
        html_content: str,
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Use Firecrawl's structured extraction (if available).

        Args:
            html_content: HTML content to extract from
            schema: Extraction schema definition

        Returns:
            List of extracted program data
        """
        # Note: Firecrawl's structured extraction API may require different endpoint
        # For now, we'll use the standard scrape endpoint with LLM extraction
        if not self.is_available():
            return []

        # This is a placeholder - actual implementation would depend on
        # Firecrawl's structured extraction API
        logger.debug("Structured extraction not yet fully implemented")
        return []

    def get_curated_institutions(self, limit: Optional[int] = None) -> List[InstitutionSeed]:
        """Get curated list of top graduate schools.

        Args:
            limit: Optional limit on number of schools to return

        Returns:
            List of InstitutionSeed objects
        """
        institutions = []
        schools = TOP_GRADUATE_SCHOOLS[:limit] if limit else TOP_GRADUATE_SCHOOLS

        for school_data in schools:
            institution = InstitutionSeed(
                name=school_data["name"],
                short_name=school_data.get("short_name"),
                website_url=school_data.get("website_url"),
                country=school_data["country"],
                state_or_province=school_data.get("state_or_province"),
                city=school_data.get("city"),
                public_private=school_data.get("public_private"),
                institution_type=school_data.get("institution_type"),
                data_source="curated_top_schools",
            )
            institutions.append(institution)

        logger.info("Loaded %d curated top graduate schools", len(institutions))
        return institutions

    async def scrape_programs_for_school(
        self,
        school_name: str,
        programs_url: str,
        max_programs: int = 20
    ) -> List[ProgramSeed]:
        """Scrape graduate programs from a school's programs page.

        Args:
            school_name: Name of the institution
            programs_url: URL of the graduate programs listing page
            max_programs: Maximum number of programs to extract

        Returns:
            List of ProgramSeed objects
        """
        if not self.is_available():
            logger.warning("Firecrawl not available - returning empty program list")
            return []

        programs = []

        try:
            # First, scrape the programs listing page
            result = self.scrape_url(programs_url, formats=["markdown", "links"])
            if not result:
                return []

            # Extract program links
            links = result.get("links", [])
            markdown = result.get("markdown", "")

            # Filter links that look like program pages
            program_patterns = [
                "/program", "/degree", "/phd", "/masters", "/graduate",
                "/doctoral", "/mba", "/ms-", "/ma-", "/meng",
            ]
            program_links = [
                link for link in links
                if any(pattern in link.lower() for pattern in program_patterns)
            ][:max_programs]

            logger.info("Found %d potential program links for %s", len(program_links), school_name)

            # For each program link, scrape basic info
            for link in program_links:
                try:
                    program_data = self._extract_program_from_url(link, school_name)
                    if program_data:
                        programs.append(program_data)
                except Exception as e:
                    logger.warning("Error scraping program %s: %s", link, e)
                    continue

        except Exception as e:
            logger.error("Error scraping programs for %s: %s", school_name, e)

        return programs

    def _extract_program_from_url(self, url: str, school_name: str) -> Optional[ProgramSeed]:
        """Extract program information from a URL.

        Args:
            url: Program page URL
            school_name: Name of the institution

        Returns:
            ProgramSeed or None
        """
        result = self.scrape_url(url, formats=["markdown"])
        if not result:
            return None

        markdown = result.get("markdown", "")
        metadata = result.get("metadata", {})

        # Extract basic info from URL and content
        title = metadata.get("title", "")

        # Determine degree level from URL/title
        degree_level = "masters"  # default
        url_lower = url.lower()
        title_lower = title.lower()
        combined = url_lower + " " + title_lower

        if "phd" in combined or "doctoral" in combined or "doctorate" in combined:
            degree_level = "phd"
        elif "mba" in combined:
            degree_level = "professional"

        # Extract program name from title
        program_name = title.split("|")[0].strip() if "|" in title else title

        if not program_name or len(program_name) < 3:
            return None

        return ProgramSeed(
            name=program_name,
            institution_name=school_name,
            degree_level=degree_level,
            website_url=url,
            description=markdown[:500] if markdown else None,
        )


# Convenience functions
def get_top_graduate_schools(limit: Optional[int] = None) -> List[InstitutionSeed]:
    """Get curated list of top graduate schools.

    This doesn't require Firecrawl API - uses built-in curated data.
    """
    scraper = FirecrawlScraper()
    return scraper.get_curated_institutions(limit)


def get_school_info(name: str) -> Optional[Dict[str, Any]]:
    """Get info for a specific school from curated list."""
    name_lower = name.lower()
    for school in TOP_GRADUATE_SCHOOLS:
        if (school["name"].lower() == name_lower or
            school.get("short_name", "").lower() == name_lower):
            return school
    return None
