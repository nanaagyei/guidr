"""Tests for URL ranking heuristics."""
import pytest
from src.pipeline.research_gateway.url_ranker import rank_url_results, _compute_score


class _FakeResult:
    """Minimal stand-in for URLDiscoveryResult."""

    def __init__(self, url: str, confidence: float = 0.5):
        self.url = url
        self.confidence = confidence


class TestComputeScore:
    """Unit tests for the scoring function."""

    def test_https_gets_boost(self):
        https_score = _compute_score("https://example.com/about", 0.5, [], [])
        http_score = _compute_score("http://example.com/about", 0.5, [], [])
        assert https_score > http_score

    def test_allowlist_domain_match(self):
        score_match = _compute_score("https://mit.edu/grad", 0.5, [], ["mit.edu"])
        score_no_match = _compute_score("https://random.com/grad", 0.5, [], ["mit.edu"])
        assert score_match > score_no_match

    def test_category_keyword_boost(self):
        score_kw = _compute_score("https://example.edu/admissions", 0.5, ["admissions"], [])
        score_no_kw = _compute_score("https://example.edu/about", 0.5, ["admissions"], [])
        assert score_kw > score_no_kw

    def test_edu_domain_boost(self):
        edu_score = _compute_score("https://stanford.edu/about", 0.5, [], [])
        com_score = _compute_score("https://stanford.com/about", 0.5, [], [])
        assert edu_score > com_score

    def test_base_confidence_matters(self):
        high = _compute_score("http://example.com", 0.9, [], [])
        low = _compute_score("http://example.com", 0.1, [], [])
        assert high > low


class TestRankUrlResults:
    """Integration tests for rank_url_results."""

    def test_empty_list_returns_empty(self):
        assert rank_url_results([], "SCHOOL_OVERVIEW") == []

    def test_https_preferred_over_http(self):
        results = [
            _FakeResult("http://mit.edu/about", 0.5),
            _FakeResult("https://mit.edu/about", 0.5),
        ]
        ranked = rank_url_results(results, "SCHOOL_OVERVIEW")
        assert ranked[0].url == "https://mit.edu/about"

    def test_allowlist_domain_ranked_first(self):
        results = [
            _FakeResult("https://random.com/grad", 0.6),
            _FakeResult("https://mit.edu/grad", 0.5),
        ]
        ranked = rank_url_results(results, "SCHOOL_OVERVIEW", allowlist=["mit.edu"])
        assert ranked[0].url == "https://mit.edu/grad"

    def test_keyword_match_boosts_ranking(self):
        results = [
            _FakeResult("https://mit.edu/about-us", 0.5),
            _FakeResult("https://mit.edu/admissions", 0.5),
        ]
        ranked = rank_url_results(results, "PROGRAM_REQUIREMENTS")
        assert ranked[0].url == "https://mit.edu/admissions"

    def test_preserves_order_for_equal_scores(self):
        results = [
            _FakeResult("https://a.edu/page1", 0.5),
            _FakeResult("https://b.edu/page2", 0.5),
        ]
        ranked = rank_url_results(results, "SCHOOL_OVERVIEW")
        # Same score → original order preserved
        assert ranked[0].url == "https://a.edu/page1"

    def test_all_signals_combined(self):
        results = [
            _FakeResult("http://random.com/info", 0.6),  # moderate confidence, HTTP, no .edu
            _FakeResult("https://mit.edu/funding", 0.3),  # HTTPS + .edu + keyword + allowlist
        ]
        ranked = rank_url_results(
            results,
            "FUNDING_OPPORTUNITIES",
            allowlist=["mit.edu"],
        )
        # .edu + HTTPS + allowlist + keyword should outweigh raw confidence
        assert ranked[0].url == "https://mit.edu/funding"
