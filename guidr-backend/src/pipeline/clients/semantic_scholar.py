"""Semantic Scholar API client for professor research data."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.config import settings
from src.pipeline.redis_keyspace import take_token

logger = logging.getLogger(__name__)

RATE_LIMIT_DOMAIN = "api.semanticscholar.org"


class SemanticScholarClient:
    """Client for the Semantic Scholar Academic Graph API.

    Rate limited to ~1 request/second via Redis token bucket.
    Docs: https://api.semanticscholar.org/api-docs/
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.semantic_scholar_api_key
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _rate_limit(self) -> None:
        """Apply Redis-based rate limit (1 rps default)."""
        result = take_token(
            RATE_LIMIT_DOMAIN,
            max_tokens=settings.semantic_scholar_rps,
            refill_rate=settings.semantic_scholar_rps,
        )
        if not result.allowed:
            import time
            wait = max(0.5, 1.0 / settings.semantic_scholar_rps)
            logger.debug("S2 rate limited, waiting %.1fs", wait)
            time.sleep(wait)

    def search_author(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search for authors by name or affiliation.

        Args:
            query: Search string (name, affiliation keywords).
            limit: Max results (up to 1000).
            fields: Author fields to return.

        Returns:
            List of author dicts.
        """
        self._rate_limit()
        if fields is None:
            fields = [
                "authorId", "name", "affiliations", "homepage",
                "paperCount", "citationCount", "hIndex",
            ]

        try:
            resp = self._client.get(
                f"{self.BASE_URL}/author/search",
                params={
                    "query": query,
                    "limit": min(limit, 1000),
                    "fields": ",".join(fields),
                },
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except httpx.HTTPStatusError as exc:
            logger.error("S2 search_author error %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("S2 search_author failed: %s", exc)
            return []

    def get_author(
        self,
        author_id: str,
        fields: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        """Get author details by Semantic Scholar author ID.

        Args:
            author_id: Semantic Scholar author ID.
            fields: Fields to return.

        Returns:
            Author dict or None.
        """
        self._rate_limit()
        if fields is None:
            fields = [
                "authorId", "externalIds", "name", "affiliations",
                "homepage", "paperCount", "citationCount", "hIndex",
            ]

        try:
            resp = self._client.get(
                f"{self.BASE_URL}/author/{author_id}",
                params={"fields": ",".join(fields)},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("S2 get_author error %d: %s", exc.response.status_code, exc)
            return None
        except Exception as exc:
            logger.error("S2 get_author failed: %s", exc)
            return None

    def get_author_papers(
        self,
        author_id: str,
        limit: int = 20,
        fields: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Get papers by an author.

        Args:
            author_id: Semantic Scholar author ID.
            limit: Max papers to return.
            fields: Paper fields to return.

        Returns:
            List of paper dicts.
        """
        self._rate_limit()
        if fields is None:
            fields = [
                "paperId", "title", "year", "citationCount",
                "venue", "publicationTypes", "openAccessPdf",
            ]

        try:
            resp = self._client.get(
                f"{self.BASE_URL}/author/{author_id}/papers",
                params={
                    "limit": min(limit, 1000),
                    "fields": ",".join(fields),
                },
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except httpx.HTTPStatusError as exc:
            logger.error("S2 get_author_papers error %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("S2 get_author_papers failed: %s", exc)
            return []

    def close(self):
        self._client.close()
