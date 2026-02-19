"""Real Perplexity Sonar API provider for URL discovery and research."""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

from src.config import settings
from src.pipeline.research_gateway.providers.base import BaseResearchProvider
from src.pipeline.research_gateway.schemas import URLDiscoveryResult

logger = logging.getLogger(__name__)

# Category -> search query templates
SEARCH_TEMPLATES = {
    "SCHOOL_OVERVIEW": "{entity_name} university overview graduate school about",
    "PROGRAM_REQUIREMENTS": "{entity_name} graduate program requirements admissions GRE GPA",
    "PROGRAM_DEADLINES": "{entity_name} graduate application deadlines dates",
    "PROGRAM_FUNDING": "{entity_name} graduate funding scholarships fellowships financial aid",
    "FACULTY_DIRECTORY": "{entity_name} faculty directory professors department",
}


class PerplexityProvider(BaseResearchProvider):
    """Real Perplexity Sonar API provider.

    Uses the Perplexity chat/completions API with the sonar model
    to discover and rank relevant URLs for graduate school data.
    """

    API_URL = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "perplexity_api_key", None)
        self._client = httpx.Client(timeout=30)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def discover_urls(
        self,
        entity_name: str,
        category: str,
        website_hint: Optional[str] = None,
        constraints: Optional[dict] = None,
    ) -> list[URLDiscoveryResult]:
        """Call Perplexity Sonar to discover relevant URLs."""
        if not self.is_available():
            logger.warning("Perplexity API key not configured, cannot discover URLs")
            return []

        max_results = (constraints or {}).get("max_results", 5)
        template = SEARCH_TEMPLATES.get(category, "{entity_name} graduate school {category}")
        query = template.format(entity_name=entity_name, category=category)

        if website_hint:
            query += f" site:{website_hint}"

        system_prompt = (
            "You are a research assistant. Find the most relevant web pages for the query. "
            "Return ONLY a JSON array of objects with keys: url, title, confidence (0-1), reason. "
            f"Return at most {max_results} results. Prioritize official .edu pages."
        )

        try:
            start = time.time()
            resp = self._client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                    ],
                    "max_tokens": 2000,
                    "return_citations": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            latency_ms = int((time.time() - start) * 1000)

            # Parse response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])

            results = self._parse_results(content, citations, category)
            logger.info(
                "Perplexity discovered %d URLs for %s/%s in %dms",
                len(results), entity_name, category, latency_ms,
            )
            return results[:max_results]

        except httpx.HTTPStatusError as exc:
            logger.error("Perplexity API error %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("Perplexity discovery failed: %s", exc)
            return []

    def _parse_results(
        self, content: str, citations: list, category: str
    ) -> list[URLDiscoveryResult]:
        """Parse Perplexity response into URLDiscoveryResult list."""
        results = []

        # Try to parse JSON from content
        try:
            # Find JSON array in content
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                parsed = json.loads(json_str)
                for item in parsed:
                    if isinstance(item, dict) and "url" in item:
                        results.append(URLDiscoveryResult(
                            url=item["url"],
                            title=item.get("title"),
                            confidence=float(item.get("confidence", 0.5)),
                            reason=item.get("reason"),
                            source="perplexity_sonar",
                        ))
        except (json.JSONDecodeError, ValueError):
            logger.debug("Could not parse JSON from Perplexity response, using citations")

        # Fall back to citations if JSON parsing failed
        if not results and citations:
            for i, citation_url in enumerate(citations[:5]):
                if isinstance(citation_url, str):
                    results.append(URLDiscoveryResult(
                        url=citation_url,
                        confidence=max(0.3, 0.8 - i * 0.1),
                        reason=f"Citation from Perplexity response",
                        source="perplexity_citation",
                    ))

        return results

    def close(self):
        self._client.close()
