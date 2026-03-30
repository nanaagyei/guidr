"""OpenAlex API client for academic author and institution data."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from src.config import settings
from src.pipeline.redis_keyspace import take_token

logger = logging.getLogger(__name__)

RATE_LIMIT_DOMAIN = "api.openalex.org"


class OpenAlexClient:
    """Client for the OpenAlex API.

    Rate limited to ~10 requests/second via Redis token bucket.
    Docs: https://docs.openalex.org/
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openalex_api_key
        self._client = httpx.Client(timeout=30)

    def _params(self, extra: Optional[dict] = None) -> dict[str, Any]:
        """Base query params with optional API key."""
        params: dict[str, Any] = {}
        if self.api_key:
            params["api_key"] = self.api_key
        if extra:
            params.update(extra)
        return params

    def _rate_limit(self) -> None:
        """Apply Redis-based rate limit (10 rps default)."""
        result = take_token(
            RATE_LIMIT_DOMAIN,
            max_tokens=settings.openalex_rps,
            refill_rate=settings.openalex_rps,
        )
        if not result.allowed:
            import time
            time.sleep(0.15)

    def search_authors(
        self,
        query: str,
        affiliation_id: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search for authors, optionally filtered by affiliation.

        Args:
            query: Free-text search (research interests, name).
            affiliation_id: OpenAlex institution ID to filter by.
            limit: Max results.

        Returns:
            List of author result dicts.
        """
        self._rate_limit()
        params = self._params({"per_page": min(limit, 200)})

        filters = []
        if affiliation_id:
            filters.append(f"last_known_institutions.id:{affiliation_id}")
        if filters:
            params["filter"] = ",".join(filters)
        params["search"] = query

        try:
            resp = self._client.get(
                f"{self.BASE_URL}/authors",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAlex search_authors error %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("OpenAlex search_authors failed: %s", exc)
            return []

    def get_author(self, author_id: str) -> Optional[dict[str, Any]]:
        """Get author details by OpenAlex ID.

        Args:
            author_id: OpenAlex author ID (e.g., "A1234567890").

        Returns:
            Author dict or None.
        """
        self._rate_limit()
        try:
            resp = self._client.get(
                f"{self.BASE_URL}/authors/{author_id}",
                params=self._params(),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("OpenAlex get_author error %d: %s", exc.response.status_code, exc)
            return None
        except Exception as exc:
            logger.error("OpenAlex get_author failed: %s", exc)
            return None

    def get_institution(self, institution_id: str) -> Optional[dict[str, Any]]:
        """Get institution details by OpenAlex ID.

        Args:
            institution_id: OpenAlex institution ID.

        Returns:
            Institution dict or None.
        """
        self._rate_limit()
        try:
            resp = self._client.get(
                f"{self.BASE_URL}/institutions/{institution_id}",
                params=self._params(),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("OpenAlex get_institution error %d: %s", exc.response.status_code, exc)
            return None
        except Exception as exc:
            logger.error("OpenAlex get_institution failed: %s", exc)
            return None

    def search_works(
        self,
        query: str,
        author_id: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search academic works (papers).

        Args:
            query: Free-text search.
            author_id: Filter by OpenAlex author ID.
            limit: Max results.

        Returns:
            List of work dicts.
        """
        self._rate_limit()
        params = self._params({"per_page": min(limit, 200)})

        filters = []
        if author_id:
            filters.append(f"authorships.author.id:{author_id}")
        if filters:
            params["filter"] = ",".join(filters)
        params["search"] = query

        try:
            resp = self._client.get(
                f"{self.BASE_URL}/works",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAlex search_works error %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("OpenAlex search_works failed: %s", exc)
            return []

    def close(self):
        self._client.close()
