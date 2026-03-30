"""Common base classes and helpers for Guidr scrapers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import httpx
from slugify import slugify

from src.config import settings


@dataclass
class InstitutionSeed:
    """Normalized institution data ready for persistence."""

    name: str
    country: str
    short_name: Optional[str] = None
    state_or_province: Optional[str] = None
    city: Optional[str] = None
    website_url: Optional[str] = None
    institution_type: Optional[str] = None
    public_private: Optional[str] = None
    ipeds_unit_id: Optional[str] = None
    scorecard_school_id: Optional[str] = None
    data_source: str = "ipeds"


@dataclass
class ProgramSeed:
    """Normalized graduate program data."""

    institution_name: str
    name: str
    degree_level: str
    field_of_study: Optional[str] = None
    description: Optional[str] = None
    application_deadline_primary: Optional[str] = None
    tuition_estimate_per_year: Optional[float] = None
    application_fee: Optional[float] = None
    website_url: Optional[str] = None
    program_features: Optional[List[str]] = None
    data_source: str = "scorecard"


class BaseFetcher:
    """Shared HTTP helper for scraper classes."""

    def __init__(self, *, timeout: int = 60):
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers = {
                "User-Agent": settings.scraper_user_agent,
            }
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client

    def download_file(self, url: str, destination: Path) -> Path:
        """Download a remote file to destination."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        response = self._get_client().get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return destination

    def slugify_name(self, value: str) -> str:
        return slugify(value)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def chunked(iterable: Iterable, size: int) -> Iterable[List]:
    """Yield lists of length size from iterable."""
    chunk: List = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

