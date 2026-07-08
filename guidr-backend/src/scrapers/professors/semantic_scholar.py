"""Placeholder Semantic Scholar client for future professor scraping."""
from __future__ import annotations

from typing import Dict, Optional

import httpx


class SemanticScholarClient:
    """Minimal client ready for future expansion."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/"

    def __init__(self, *, timeout: int = 30):
        self._client = httpx.Client(timeout=timeout)

    def lookup_author(self, author_id: str, fields: Optional[str] = None) -> Dict:
        url = f"{self.BASE_URL}author/{author_id}"
        params = {"fields": fields or "name,affiliations,paperCount,citationCount"}
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
