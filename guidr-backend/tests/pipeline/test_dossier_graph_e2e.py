"""Integration test for full DossierGraph with stub provider."""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal


class TestDossierGraphE2E:
    """End-to-end tests for DossierGraph with mocked external services."""

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    @patch("src.pipeline.research_gateway.service._select_provider")
    @patch("src.pipeline.research_gateway.service._get_redis")
    def test_school_dossier_full_flow(self, mock_redis, mock_provider, mock_get_db):
        """Test full school dossier flow: load → research → validate → score → stage."""
        # Mock DB
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inst = MagicMock()
        mock_inst.name = "MIT"
        mock_inst.website_url = "https://mit.edu"
        mock_inst.description = None
        mock_inst.acceptance_rate = None
        mock_inst.enrollment_total = None

        # Return institution on first call, None on cache checks
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_inst,  # load_context: institution lookup
            None,       # stage_dossier: cache lookup
        ]

        # Mock Redis (no cache)
        mock_redis.return_value = None

        # Mock provider to return dossier
        from src.pipeline.research_gateway.schemas import DossierResponse, DossierCitation, Metrics

        mock_prov = MagicMock()
        mock_prov.run.return_value = DossierResponse(
            status="SUCCESS",
            final_json={
                "description": "MIT is a world-class research university [c1]",
                "acceptance_rate": 3.9,
                "enrollment_total": 11000,
                "grad_enrollment": 6900,
                "campus_setting": "urban",
                "academic_calendar": "semester",
            },
            citations=[
                DossierCitation(id="c1", url="https://mit.edu/about"),
                DossierCitation(id="c2", url="https://nces.ed.gov/mit"),
            ],
            evidence_map={"description": ["c1"]},
            metrics=Metrics(latency_ms=1500),
        )
        mock_provider.return_value = mock_prov

        # Run graph
        from src.pipeline.orchestrator.dossier_graph import create_dossier_graph

        graph = create_dossier_graph(checkpointer=None)
        initial_state = {
            "job_type": "school_dossier",
            "entity_kind": "school",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "progress": [],
        }

        result = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": "dossier-e2e-full"}},
        )

        # Verify flow completed
        assert "load_dossier_context" in result.get("progress", [])
        assert "research_extract" in result.get("progress", [])
        assert "validate_citations" in result.get("progress", [])
        assert "score_dossier_confidence" in result.get("progress", [])
        assert result.get("dossier_json", {}).get("description") is not None

    @patch("src.pipeline.orchestrator.dossier_nodes._get_db")
    @patch("src.pipeline.research_gateway.service._select_provider")
    @patch("src.pipeline.research_gateway.service._get_redis")
    def test_low_confidence_triggers_fallback_path(self, mock_redis, mock_provider, mock_get_db):
        """Test that low confidence routes to fallback (or stage_low)."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_redis.return_value = None

        from src.pipeline.research_gateway.schemas import DossierResponse, Metrics

        mock_prov = MagicMock()
        mock_prov.run.return_value = DossierResponse(
            status="PARTIAL",
            final_json={"description": "Some school"},
            citations=[],
            evidence_map={},
            metrics=Metrics(latency_ms=1000),
        )
        mock_provider.return_value = mock_prov

        from src.pipeline.orchestrator.dossier_graph import create_dossier_graph

        with patch("src.config.settings") as mock_settings:
            mock_settings.enable_scrape_fallback = False

            graph = create_dossier_graph(checkpointer=None)
            initial_state = {
                "job_type": "school_dossier",
                "entity_kind": "school",
                "entity_id": "550e8400-e29b-41d4-a716-446655440000",
                "progress": [],
            }

            result = graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": "dossier-e2e-fallback"}},
            )

        # Should still stage even with low confidence
        assert "score_dossier_confidence" in result.get("progress", [])
        assert "stage_dossier" in result.get("progress", [])
