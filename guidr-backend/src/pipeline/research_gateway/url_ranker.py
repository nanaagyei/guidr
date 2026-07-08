"""URL ranking heuristics for research gateway results.

Post-processes URL discovery results to prioritize quality signals:
- HTTPS preference
- Allowlist domain matching
- Category keyword boosting
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Category-specific keywords that boost URL relevance.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "SCHOOL_OVERVIEW": ["about", "overview", "graduate", "admissions", "academics"],
    "PROGRAM_REQUIREMENTS": ["admissions", "requirements", "apply", "phd", "masters", "program"],
    "FACULTY_DIRECTORY": ["faculty", "people", "directory", "professors", "staff", "department"],
    "FUNDING_OPPORTUNITIES": ["funding", "financial-aid", "fellowships", "scholarships", "tuition"],
    "DEADLINES": ["deadlines", "dates", "calendar", "apply", "admissions"],
}

# Score weights
_HTTPS_BOOST = 10
_ALLOWLIST_BOOST = 20
_KEYWORD_BOOST = 15
_EDU_BOOST = 5


def rank_url_results(
    results: list,
    category: str,
    allowlist: Optional[list[str]] = None,
) -> list:
    """Re-rank URL discovery results by quality heuristics.

    Args:
        results: List of URLDiscoveryResult objects with `url` and `confidence` attrs.
        category: Research category (e.g., "SCHOOL_OVERVIEW").
        allowlist: Optional list of preferred domain patterns.

    Returns:
        The same list sorted by composite score (descending).
    """
    if not results:
        return results

    allowlist = allowlist or []
    keywords = CATEGORY_KEYWORDS.get(category, [])
    scored: list[tuple[float, int, object]] = []

    for idx, result in enumerate(results):
        score = _compute_score(result.url, result.confidence, keywords, allowlist)
        # Use negative idx as tiebreaker to preserve original order
        scored.append((score, -idx, result))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [item[2] for item in scored]


def _compute_score(
    url: str,
    base_confidence: float,
    keywords: list[str],
    allowlist: list[str],
) -> float:
    """Compute composite ranking score for a single URL."""
    score = base_confidence * 100  # Normalize 0-1 confidence to 0-100

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path.lower()

    # HTTPS preference
    if parsed.scheme == "https":
        score += _HTTPS_BOOST

    # .edu domain boost
    if hostname.endswith(".edu"):
        score += _EDU_BOOST

    # Allowlist domain match
    for domain in allowlist:
        domain_lower = domain.lower()
        if hostname == domain_lower or hostname.endswith("." + domain_lower):
            score += _ALLOWLIST_BOOST
            break

    # Category keyword boost — check URL path for relevant keywords
    for keyword in keywords:
        if keyword in path:
            score += _KEYWORD_BOOST
            break  # Only count once

    return score
