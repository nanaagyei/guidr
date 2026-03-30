"""Unit tests for dossier graph nodes with mocked providers."""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


class TestLoadDossierContext:
    """Tests for load_dossier_context node."""

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_loads_school_context(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inst = MagicMock()
        mock_inst.name = "MIT"
        mock_inst.website_url = "https://mit.edu"
        mock_inst.description = "Research university"
        mock_inst.acceptance_rate = Decimal("3.9")
        mock_inst.enrollment_total = 11000
        mock_db.query.return_value.filter.return_value.first.return_value = mock_inst

        from src.pipeline.orchestrator.dossier_nodes import load_dossier_context

        state = {
            "entity_kind": "school",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "job_type": "school_dossier",
            "progress": [],
        }
        result = load_dossier_context(state)

        assert result["entity_name"] == "MIT"
        assert result["website_hint"] == "https://mit.edu"
        assert "load_dossier_context" in result["progress"]

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_loads_user_profile_for_recommendations(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # No institution query needed for recommendation_run
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock user profile
        mock_profile = MagicMock()
        mock_profile.intended_degree = "PhD"
        mock_profile.primary_field_of_study = "Computer Science"
        mock_profile.gpa = Decimal("3.8")
        mock_profile.preferred_countries = ["US", "UK"]
        mock_profile.funding_priority = "high"
        mock_profile.program_style_preference = "research"

        # No entity_id in state → institution query skipped → profile is first query
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_profile]

        from src.pipeline.orchestrator.dossier_nodes import load_dossier_context

        state = {
            "entity_kind": "school",
            "job_type": "recommendation_run",
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "progress": [],
        }
        result = load_dossier_context(state)

        assert result["user_profile"]["degree_level"] == "PhD"
        assert result["user_profile"]["field_of_study"] == "Computer Science"


class TestValidateCitations:
    """Tests for validate_citations node."""

    def test_no_dossier_data(self):
        from src.pipeline.orchestrator.dossier_nodes import validate_citations

        state = {"dossier_json": {}, "dossier_evidence_map": {}, "dossier_citations": [], "progress": []}
        result = validate_citations(state)

        assert result["citation_coverage"] == 0.0
        assert "No dossier data extracted" in result["citation_issues"]

    def test_full_coverage(self):
        from src.pipeline.orchestrator.dossier_nodes import validate_citations

        state = {
            "dossier_json": {"name": "MIT [c1]", "city": "Cambridge [c2]"},
            "dossier_evidence_map": {"name": ["c1"], "city": ["c2"]},
            "dossier_citations": [
                {"id": "c1", "url": "https://mit.edu"},
                {"id": "c2", "url": "https://mit.edu/about"},
            ],
            "progress": [],
        }
        result = validate_citations(state)

        assert result["citation_coverage"] == 1.0

    def test_no_citations_warns(self):
        from src.pipeline.orchestrator.dossier_nodes import validate_citations

        state = {
            "dossier_json": {"name": "MIT", "city": "Cambridge"},
            "dossier_evidence_map": {},
            "dossier_citations": [],
            "progress": [],
        }
        result = validate_citations(state)

        assert "No citations returned by provider" in result["citation_issues"]


class TestScoreDossierConfidence:
    """Tests for score_dossier_confidence node."""

    def test_empty_dossier_scores_zero(self):
        from src.pipeline.orchestrator.dossier_nodes import score_dossier_confidence

        state = {
            "dossier_json": {},
            "citation_coverage": 0.0,
            "dossier_citations": [],
            "dossier_errors": [],
            "entity_kind": "school",
            "progress": [],
        }
        result = score_dossier_confidence(state)

        assert result["confidence"] == 0.0
        assert result["needs_fallback"] is True

    def test_errors_score_zero(self):
        from src.pipeline.orchestrator.dossier_nodes import score_dossier_confidence

        state = {
            "dossier_json": {"name": "MIT"},
            "citation_coverage": 0.8,
            "dossier_citations": [{"id": "c1", "url": "https://mit.edu"}],
            "dossier_errors": ["API error"],
            "entity_kind": "school",
            "progress": [],
        }
        result = score_dossier_confidence(state)

        assert result["confidence"] == 0.0

    def test_high_confidence_promotes(self):
        from src.pipeline.orchestrator.dossier_nodes import score_dossier_confidence

        state = {
            "dossier_json": {
                "description": "MIT is a research university [c1]",
                "acceptance_rate": 3.9,
                "enrollment_total": 11000,
                "grad_enrollment": 6000,
                "campus_setting": "urban",
                "academic_calendar": "semester",
            },
            "citation_coverage": 1.0,
            "dossier_citations": [
                {"id": "c1", "url": "https://mit.edu/about"},
                {"id": "c2", "url": "https://nces.ed.gov"},
            ],
            "dossier_errors": [],
            "entity_kind": "school",
            "progress": [],
        }
        result = score_dossier_confidence(state)

        assert result["confidence"] > 0.70
        assert result["needs_fallback"] is False


class TestStageDossier:
    """Tests for stage_dossier node."""

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_creates_cache_entry(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from src.pipeline.orchestrator.dossier_nodes import stage_dossier

        state = {
            "dossier_json": {"name": "MIT"},
            "entity_kind": "school",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "confidence": 0.85,
            "job_type": "school_dossier",
            "dossier_citations": [{"id": "c1", "url": "https://mit.edu"}],
            "dossier_evidence_map": {"name": ["c1"]},
            "progress": [],
        }
        result = stage_dossier(state)

        assert "stage_dossier" in result["progress"]
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    def test_uses_user_id_for_recommendations(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from src.pipeline.orchestrator.dossier_nodes import stage_dossier

        state = {
            "dossier_json": {"recommendations": []},
            "entity_kind": "school",
            "entity_id": None,
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "confidence": 0.80,
            "job_type": "recommendation_run",
            "dossier_citations": [],
            "dossier_evidence_map": {},
            "progress": [],
        }
        result = stage_dossier(state)

        assert "stage_dossier" in result["progress"]
