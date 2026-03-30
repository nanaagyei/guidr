"""Unit tests for orchestrator graph nodes with heavy mocking."""
import pytest
from unittest.mock import patch, MagicMock
import uuid

import src.db as db_mod


ENTITY_ID = "550e8400-e29b-41d4-a716-446655440000"


def _get_nodes_mod():
    """Import the nodes module for patch.object usage."""
    from src.pipeline.orchestrator import nodes as mod
    return mod


# ------------------------------------------------------------------
# load_context
# ------------------------------------------------------------------


class TestLoadContextSetsEntityName:
    """load_context should populate entity_name from the DB entity."""

    def test_load_context_sets_entity_name_from_db(self):
        mod = _get_nodes_mod()
        mock_db = MagicMock()

        mock_inst = MagicMock()
        mock_inst.name = "Stanford University"
        mock_inst.website_url = "https://stanford.edu"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_inst
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            state = {
                "entity_kind": "school",
                "entity_id": ENTITY_ID,
                "progress": [],
            }
            result = mod.load_context(state)

            assert result["entity_name"] == "Stanford University"
            assert result["website_hint"] == "https://stanford.edu"
            assert "load_context" in result["progress"]
            mock_db.close.assert_called_once()


class TestLoadContextKnownSources:
    """load_context should populate known_sources from SourceDocument rows."""

    def test_load_context_loads_known_sources(self):
        mod = _get_nodes_mod()
        mock_db = MagicMock()

        mock_inst = MagicMock()
        mock_inst.name = "MIT"
        mock_inst.website_url = "https://mit.edu"

        mock_doc = MagicMock()
        mock_doc.canonical_url = "https://mit.edu/programs"
        mock_doc.purpose = "SCHOOL_OVERVIEW"
        mock_doc.id = uuid.uuid4()

        # first() returns institution, all() returns source docs
        mock_db.query.return_value.filter.return_value.first.return_value = mock_inst
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_doc]

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            state = {
                "entity_kind": "school",
                "entity_id": ENTITY_ID,
                "progress": [],
            }
            result = mod.load_context(state)

            assert len(result["known_sources"]) == 1
            assert result["known_sources"][0]["url"] == "https://mit.edu/programs"
            assert result["need_discovery"] is False


class TestLoadContextNeedDiscovery:
    """load_context should set need_discovery when no sources and no website_hint."""

    def test_load_context_sets_need_discovery_when_no_sources(self):
        mod = _get_nodes_mod()
        mock_db = MagicMock()

        mock_inst = MagicMock()
        mock_inst.name = "Unknown U"
        mock_inst.website_url = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_inst
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            state = {
                "entity_kind": "school",
                "entity_id": ENTITY_ID,
                "progress": [],
            }
            result = mod.load_context(state)

            assert result["need_discovery"] is True
            assert result["known_sources"] == []


# ------------------------------------------------------------------
# discover_urls
# ------------------------------------------------------------------


class TestDiscoverUrls:
    """Tests for the discover_urls node."""

    def test_discover_urls_calls_gateway(self):
        mod = _get_nodes_mod()
        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.url = "https://stanford.edu/admissions"
        mock_result.source = "perplexity"

        mock_resp = MagicMock()
        mock_resp.results = [mock_result]
        mock_service.run.return_value = mock_resp

        with patch.object(db_mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "ResearchGatewayService", return_value=mock_service):
            state = {
                "entity_kind": "school",
                "entity_id": ENTITY_ID,
                "entity_name": "Stanford",
                "category": "SCHOOL_OVERVIEW",
                "website_hint": None,
                "progress": [],
            }
            result = mod.discover_urls(state)

            mock_service.run.assert_called_once()
            assert result["candidate_urls"] == ["https://stanford.edu/admissions"]
            assert result["target_url"] == "https://stanford.edu/admissions"
            assert "discover_urls" in result["progress"]

    def test_discover_urls_persists_documents(self):
        mod = _get_nodes_mod()
        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.url = "https://example.edu/grad"
        mock_result.source = "perplexity"

        mock_resp = MagicMock()
        mock_resp.results = [mock_result]
        mock_service.run.return_value = mock_resp

        with patch.object(db_mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "ResearchGatewayService", return_value=mock_service):
            state = {
                "entity_kind": "school",
                "entity_id": ENTITY_ID,
                "entity_name": "Example U",
                "category": "SCHOOL_OVERVIEW",
                "progress": [],
            }
            mod.discover_urls(state)

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()


# ------------------------------------------------------------------
# canonicalize_urls
# ------------------------------------------------------------------


class TestCanonicalizeUrls:
    """Tests for the canonicalize_urls node."""

    def test_canonicalize_uses_candidates_first(self):
        mod = _get_nodes_mod()

        state = {
            "candidate_urls": ["https://a.edu", "https://b.edu"],
            "target_url": "https://a.edu",
            "known_sources": [{"url": "https://old.edu"}],
            "website_hint": "https://hint.edu",
            "progress": [],
        }
        result = mod.canonicalize_urls(state)

        assert result["target_url"] == "https://a.edu"

    def test_canonicalize_falls_back_to_known_sources(self):
        mod = _get_nodes_mod()

        state = {
            "candidate_urls": [],
            "target_url": None,
            "known_sources": [{"url": "https://known.edu/grad"}],
            "website_hint": "https://hint.edu",
            "progress": [],
        }
        result = mod.canonicalize_urls(state)

        assert result["target_url"] == "https://known.edu/grad"

    def test_canonicalize_falls_back_to_website_hint(self):
        mod = _get_nodes_mod()

        state = {
            "candidate_urls": [],
            "target_url": None,
            "known_sources": [],
            "website_hint": "https://hint.edu",
            "progress": [],
        }
        result = mod.canonicalize_urls(state)

        assert result["target_url"] == "https://hint.edu"


# ------------------------------------------------------------------
# fetch_page
# ------------------------------------------------------------------


class TestFetchPage:
    """Tests for the fetch_page node."""

    def test_fetch_page_blocked_domain_returns_error(self):
        mod = _get_nodes_mod()
        from src.pipeline.services import domain_health_service as dhs_mod
        from src.pipeline import redis_keyspace as rk_mod

        mock_health = MagicMock()
        mock_health.is_blocked.return_value = True

        with patch.object(dhs_mod, "DomainHealthService", return_value=mock_health):
            state = {
                "target_url": "https://blocked.edu/page",
                "progress": [],
            }
            result = mod.fetch_page(state)

            assert result["status"] == "failed"
            assert "blocked" in result["error"].lower()

    def test_fetch_page_success_records_health(self):
        mod = _get_nodes_mod()
        from src.pipeline.services import domain_health_service as dhs_mod
        from src.pipeline import redis_keyspace as rk_mod
        from src.pipeline import clients as clients_mod

        mock_health = MagicMock()
        mock_health.is_blocked.return_value = False

        mock_token = MagicMock()
        mock_token.allowed = True

        mock_client = MagicMock()
        mock_client.scrape_url.return_value = {
            "markdown": "# Hello World\nSome content here.",
            "metadata": {"statusCode": 200},
        }

        with patch.object(dhs_mod, "DomainHealthService", return_value=mock_health), \
             patch.object(rk_mod, "take_token_for_url", return_value=mock_token), \
             patch.object(clients_mod, "EnhancedFirecrawlClient", return_value=mock_client):
            state = {
                "target_url": "https://example.edu/grad",
                "progress": [],
            }
            result = mod.fetch_page(state)

            assert "raw_content" in result
            assert result["raw_content"] == "# Hello World\nSome content here."
            assert "content_hash" in result
            assert "fetched_at" in result
            mock_health.record_success.assert_called_once()


# ------------------------------------------------------------------
# extract_structured
# ------------------------------------------------------------------


class TestExtractStructured:
    """Tests for the extract_structured node."""

    def test_extract_dispatches_funding_extractor(self):
        mod = _get_nodes_mod()
        from src.pipeline import extractors as ext_mod

        mock_extractor = MagicMock()
        mock_extractor.extract_from_markdown.return_value = {
            "name": "Fellowship",
            "amount_min": 20000,
        }

        with patch.object(ext_mod, "FundingExtractor", return_value=mock_extractor):
            state = {
                "entity_kind": "funding",
                "category": "FUNDING_OVERVIEW",
                "raw_content": "# Fellowship details",
                "target_url": "https://example.edu/funding",
                "progress": [],
            }
            result = mod.extract_structured(state)

            assert result["extracted"]["name"] == "Fellowship"
            assert "extract_structured" in result["progress"]

    def test_extract_dispatches_overview_by_default(self):
        mod = _get_nodes_mod()
        from src.pipeline import extractors as ext_mod

        mock_extractor = MagicMock()
        mock_extractor.extract_from_markdown.return_value = {
            "description": "A great university",
        }

        with patch.object(ext_mod, "OverviewExtractor", return_value=mock_extractor):
            state = {
                "entity_kind": "school",
                "category": "SCHOOL_OVERVIEW",
                "raw_content": "# About Us",
                "target_url": "https://example.edu",
                "progress": [],
            }
            result = mod.extract_structured(state)

            assert result["extracted"]["description"] == "A great university"

    def test_extract_handles_exception_gracefully(self):
        mod = _get_nodes_mod()
        from src.pipeline import extractors as ext_mod

        with patch.object(ext_mod, "OverviewExtractor") as mock_cls:
            mock_cls.return_value.extract_from_markdown.side_effect = RuntimeError("LLM down")

            state = {
                "entity_kind": "school",
                "category": "SCHOOL_OVERVIEW",
                "raw_content": "Some content",
                "target_url": "https://example.edu",
                "progress": [],
            }
            result = mod.extract_structured(state)

        assert "extracted" in result
        assert result["extracted"]["source"] == "fallback"


# ------------------------------------------------------------------
# score_confidence
# ------------------------------------------------------------------


class TestScoreConfidence:
    """Tests for the score_confidence node."""

    def test_score_confidence_sets_promote_flag(self):
        mod = _get_nodes_mod()
        from src.pipeline import processors as proc_mod

        mock_scorer = MagicMock()
        mock_scorer.compute.return_value = 0.92
        mock_scorer.should_promote.return_value = True
        mock_scorer.should_repair.return_value = False

        with patch.object(proc_mod, "ConfidenceScorer", return_value=mock_scorer):
            state = {
                "entity_kind": "school",
                "extracted": {"description": "A university"},
                "validation_errors": [],
                "target_url": "https://example.edu",
                "website_hint": "https://example.edu",
                "fetched_at": "2026-03-01T12:00:00",
                "retry_count": 0,
                "progress": [],
            }
            result = mod.score_confidence(state)

            assert result["confidence"] == 0.92
            assert result["promote"] is True
            assert result["repair"] is False
            assert "score_confidence" in result["progress"]

    def test_score_confidence_sets_repair_flag(self):
        mod = _get_nodes_mod()
        from src.pipeline import processors as proc_mod

        mock_scorer = MagicMock()
        mock_scorer.compute.return_value = 0.35
        mock_scorer.should_promote.return_value = False
        mock_scorer.should_repair.return_value = True

        with patch.object(proc_mod, "ConfidenceScorer", return_value=mock_scorer):
            state = {
                "entity_kind": "school",
                "extracted": {"description": "Sparse data"},
                "validation_errors": [],
                "target_url": "https://example.edu",
                "website_hint": "https://example.edu",
                "fetched_at": "2026-03-01T12:00:00",
                "retry_count": 0,
                "progress": [],
            }
            result = mod.score_confidence(state)

            assert result["confidence"] == 0.35
            assert result["promote"] is False
            assert result["repair"] is True
