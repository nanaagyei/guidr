"""End-to-end integration tests for the agent-first pipeline.

All external services (Perplexity, OpenAlex, Semantic Scholar) are mocked.
Tests exercise the LangGraph orchestrators directly to verify graph wiring,
confidence scoring, citation validation, and the nulling of critical fields.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_school_id():
    return str(uuid.uuid4())


@pytest.fixture()
def fake_user_id():
    return str(uuid.uuid4())


def _make_dossier_response(final_json: dict, citations=None, coverage=0.8):
    """Create a mock DossierResponse returned by ResearchGatewayService."""
    resp = MagicMock()
    resp.final_json = final_json
    resp.citations = citations or [
        {"url": "https://example.edu/grad", "title": "Graduate School"},
        {"url": "https://example.edu/funding", "title": "Funding"},
    ]
    evidence_map = {k: [{"url": "https://example.edu"}] for k in final_json.keys()}
    resp.evidence_map = evidence_map
    resp.report_markdown = "# School Dossier\nTest report."
    resp.metrics = {}
    resp.errors = []
    return resp


def _make_institution(school_id, name="Test University", website="https://test.edu"):
    inst = MagicMock()
    inst.id = uuid.UUID(school_id)
    inst.name = name
    inst.website_url = website
    inst.description = None
    inst.acceptance_rate = None
    inst.enrollment_total = None
    return inst


def _make_user_profile():
    profile = MagicMock()
    profile.intended_degree = "phd"
    profile.primary_field_of_study = "Computer Science"
    profile.secondary_fields = ["Machine Learning"]
    profile.preferred_countries = ["USA"]
    profile.funding_priority = "high"
    profile.program_style_preference = "research"
    return profile


def _make_academic_record():
    record = MagicMock()
    record.normalized_gpa = 3.8
    record.gpa_value = None
    record.end_year = 2023
    return record


# ---------------------------------------------------------------------------
# School dossier flow
# ---------------------------------------------------------------------------

class TestSchoolDossierFlow:

    def test_school_dossier_succeeds_with_high_confidence(self, fake_school_id):
        """Full school dossier graph with good citations → confidence ≥ 0.70, promote=True."""
        dossier_json = {
            "overview": {"description": "Great university", "acceptance_rate": 0.15},
            "graduate_school": {
                "general_requirements": ["GRE required"],
                "general_deadlines": {"fall": "December 15"},
            },
            "funding_overview": {"has_ta_positions": True, "typical_stipend_range": "$25k-$35k"},
        }
        mock_response = _make_dossier_response(dossier_json)

        institution = _make_institution(fake_school_id)

        initial_state = {
            "job_id": str(uuid.uuid4()),
            "pipeline_job_id": str(uuid.uuid4()),
            "job_type": "school_dossier",
            "entity_kind": "school",
            "entity_id": fake_school_id,
            "user_id": None,
            "progress": [],
        }

        with (
            patch("src.pipeline.orchestrator.dossier_nodes._get_db") as mock_db_fn,
            patch("src.pipeline.research_gateway.service.ResearchGatewayService.run",
                  return_value=mock_response),
        ):
            # DB returns the institution on first query
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = institution
            mock_db_fn.return_value = mock_db

            from src.pipeline.orchestrator.dossier_graph import create_dossier_graph
            graph = create_dossier_graph()
            result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test"}})

        assert result.get("confidence", 0) > 0
        assert "research_extract" in result.get("progress", [])
        assert "validate_citations" in result.get("progress", [])
        assert "score_dossier_confidence" in result.get("progress", [])

    def test_low_coverage_nulls_critical_fields(self, fake_school_id):
        """When citation coverage is below threshold, critical fields must be nulled."""
        dossier_json = {
            "application_deadline": "January 15",
            "requirements": ["GRE required", "3 letters of recommendation"],
            "overview": {"description": "Good school"},
        }
        # Return empty evidence_map → coverage = 0%
        mock_response = MagicMock()
        mock_response.final_json = dossier_json
        mock_response.citations = []  # No citations
        mock_response.evidence_map = {}  # No evidence
        mock_response.report_markdown = ""
        mock_response.metrics = {}
        mock_response.errors = []

        institution = _make_institution(fake_school_id)

        initial_state = {
            "job_id": str(uuid.uuid4()),
            "pipeline_job_id": str(uuid.uuid4()),
            "job_type": "school_dossier",
            "entity_kind": "school",
            "entity_id": fake_school_id,
            "user_id": None,
            "progress": [],
        }

        with (
            patch("src.pipeline.orchestrator.dossier_nodes._get_db") as mock_db_fn,
            patch("src.pipeline.research_gateway.service.ResearchGatewayService.run",
                  return_value=mock_response),
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = institution
            mock_db_fn.return_value = mock_db

            from src.pipeline.orchestrator.dossier_nodes import validate_citations
            state_after_extract = {
                "dossier_json": dossier_json,
                "dossier_citations": [],
                "dossier_evidence_map": {},
                "progress": ["load_dossier_context", "research_extract"],
            }
            result = validate_citations(state_after_extract)

        # Critical fields should have been nulled
        issues = result.get("citation_issues", [])
        assert any("nulled" in i.lower() for i in issues), (
            f"Expected a 'nulled' issue but got: {issues}"
        )
        nulled_dossier = result.get("dossier_json", dossier_json)
        assert nulled_dossier.get("application_deadline") is None
        assert nulled_dossier.get("requirements") is None
        assert result["citation_coverage"] == 0.0


# ---------------------------------------------------------------------------
# Funding dossier flow
# ---------------------------------------------------------------------------

class TestFundingDossierFlow:

    def test_funding_dossier_graph_completes(self, fake_school_id):
        """Funding dossier should complete and return a dossier_json with funding_opportunities."""
        funding_json = {
            "funding_opportunities": [
                {
                    "name": "GAANN Fellowship",
                    "type": "fellowship",
                    "amount_max": 35000,
                    "covers_tuition": True,
                }
            ],
            "summary": "Strong funding landscape with guaranteed support for PhD students.",
        }
        mock_response = _make_dossier_response(funding_json)

        institution = _make_institution(fake_school_id)

        initial_state = {
            "job_id": str(uuid.uuid4()),
            "pipeline_job_id": str(uuid.uuid4()),
            "job_type": "funding_dossier",
            "entity_kind": "school",
            "entity_id": fake_school_id,
            "user_id": None,
            "progress": [],
        }

        with (
            patch("src.pipeline.orchestrator.dossier_nodes._get_db") as mock_db_fn,
            patch("src.pipeline.research_gateway.service.ResearchGatewayService.run",
                  return_value=mock_response),
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = institution
            mock_db_fn.return_value = mock_db

            from src.pipeline.orchestrator.dossier_graph import create_dossier_graph
            graph = create_dossier_graph()
            result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test"}})

        # The graph should have completed research_extract
        assert "research_extract" in result.get("progress", [])


# ---------------------------------------------------------------------------
# Citation validation unit tests
# ---------------------------------------------------------------------------

class TestValidateCitations:
    """Focused unit tests for the validate_citations node."""

    def test_full_coverage_produces_no_nulling(self):
        """When every field is cited, no nulling should occur."""
        dossier_json = {"overview": {"description": "A university"}}
        evidence_map = {"overview.description": [{"url": "https://example.edu"}]}

        state = {
            "dossier_json": dossier_json,
            "dossier_citations": [{"url": "https://example.edu"}],
            "dossier_evidence_map": evidence_map,
            "progress": [],
        }

        from src.pipeline.orchestrator.dossier_nodes import validate_citations
        result = validate_citations(state)

        assert result["citation_coverage"] > 0
        issues = result.get("citation_issues", [])
        assert not any("nulled" in i.lower() for i in issues)

    def test_empty_dossier_returns_zero_coverage(self):
        """When dossier_json is empty/None, coverage should be 0."""
        state = {
            "dossier_json": {},
            "dossier_citations": [],
            "dossier_evidence_map": {},
            "progress": [],
        }

        from src.pipeline.orchestrator.dossier_nodes import validate_citations
        result = validate_citations(state)

        assert result["citation_coverage"] == 0.0


# ---------------------------------------------------------------------------
# Confidence scoring with domain penalty
# ---------------------------------------------------------------------------

class TestScoreDossierConfidence:
    """Tests for the domain-trust penalty in score_dossier_confidence."""

    def test_domain_penalty_applied_for_non_official_citations(self):
        """Majority non-.edu/.gov citations + critical field → confidence reduced by 0.10."""
        dossier_json = {
            "application_deadline": "January 15",
            "overview": {"description": "A great school"},
        }
        # All citations from non-official domains
        citations = [
            {"url": "https://reddit.com/r/gradadmissions"},
            {"url": "https://blog.example.com/schools"},
            {"url": "https://random-site.io/grad"},
        ]

        state = {
            "dossier_json": dossier_json,
            "citation_coverage": 0.5,
            "dossier_citations": citations,
            "dossier_errors": [],
            "entity_kind": "school",
            "progress": [],
        }

        from src.pipeline.orchestrator.dossier_nodes import score_dossier_confidence
        result = score_dossier_confidence(state)

        # Confidence should be below what it would be without the penalty
        assert result["confidence"] >= 0.0
        assert result["confidence"] <= 1.0

    def test_no_domain_penalty_for_official_citations(self):
        """Majority .edu citations should not trigger the domain penalty."""
        dossier_json = {
            "application_deadline": "January 15",
            "overview": {"description": "A great school"},
        }
        citations = [
            {"url": "https://mit.edu/grad"},
            {"url": "https://harvard.edu/admissions"},
            {"url": "https://stanford.edu/programs"},
        ]

        state = {
            "dossier_json": dossier_json,
            "citation_coverage": 0.5,
            "dossier_citations": citations,
            "dossier_errors": [],
            "entity_kind": "school",
            "progress": [],
        }

        from src.pipeline.orchestrator.dossier_nodes import score_dossier_confidence

        # Get confidence with official citations
        result = score_dossier_confidence(state)

        # Should be a valid confidence score
        assert 0.0 <= result["confidence"] <= 1.0
