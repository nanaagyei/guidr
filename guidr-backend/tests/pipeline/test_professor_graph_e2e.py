"""Integration test for full ProfessorMatchGraph with mocked APIs."""
import pytest
from unittest.mock import patch, MagicMock


class TestProfessorMatchGraphE2E:
    """End-to-end tests for ProfessorMatchGraph."""

    @patch("src.pipeline.orchestrator.professor_nodes._get_db")
    @patch("src.pipeline.clients.openalex.OpenAlexClient")
    @patch("src.pipeline.clients.semantic_scholar.SemanticScholarClient")
    @patch("src.pipeline.research_gateway.service._select_provider")
    @patch("src.pipeline.research_gateway.service._get_redis")
    def test_full_professor_match_flow(
        self, mock_redis, mock_provider, MockS2Client, MockOAClient, mock_get_db
    ):
        """Test full flow: load → OpenAlex → S2 enrich → synthesize → stage → promote."""
        # Mock DB
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inst = MagicMock()
        mock_inst.name = "Stanford University"
        # Return institution, then None for subsequent queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_inst,  # load: institution
            None,       # stage: cache lookup
            None,       # stage: professor lookup by openalex_id
            None,       # stage: professor lookup by s2_id
            None,       # stage: professor lookup by name
            None,       # promote: professor lookup by name
        ]

        mock_redis.return_value = None

        # Mock OpenAlex
        mock_oa = MagicMock()
        MockOAClient.return_value = mock_oa
        mock_oa.search_authors.return_value = [
            {
                "id": "A111",
                "display_name": "Prof Alpha",
                "works_count": 50,
                "cited_by_count": 2000,
                "last_known_institutions": [{"display_name": "Stanford"}],
                "topics": [{"display_name": "NLP"}],
            }
        ]

        # Mock Semantic Scholar
        mock_s2 = MagicMock()
        MockS2Client.return_value = mock_s2
        mock_s2.search_author.return_value = [
            {
                "authorId": "S2_111",
                "name": "Prof Alpha",
                "hIndex": 30,
                "paperCount": 50,
                "citationCount": 2000,
            }
        ]
        mock_s2.get_author_papers.return_value = [
            {"title": "NLP Advances", "year": 2024, "citationCount": 15}
        ]

        # Mock Perplexity synthesis
        from src.pipeline.research_gateway.schemas import DossierResponse, DossierCitation, Metrics

        mock_prov = MagicMock()
        mock_prov.run.return_value = DossierResponse(
            status="SUCCESS",
            final_json={
                "ranked_professors": [
                    {
                        "name": "Prof Alpha",
                        "openalex_id": "A111",
                        "semantic_scholar_id": "S2_111",
                        "title": "Associate Professor",
                        "research_summary": "Expert in NLP [c1]",
                        "relevance_score": 92,
                        "h_index": 30,
                        "key_papers": [{"title": "NLP Advances", "year": 2024}],
                    }
                ],
                "methodology": "Ranked by research relevance",
            },
            citations=[DossierCitation(id="c1", url="https://stanford.edu/~alpha")],
            evidence_map={"ranked_professors[0].research_summary": ["c1"]},
            metrics=Metrics(latency_ms=2000),
        )
        mock_provider.return_value = mock_prov

        # Run graph
        from src.pipeline.orchestrator.professor_graph import create_professor_match_graph

        graph = create_professor_match_graph(checkpointer=None)
        initial_state = {
            "entity_kind": "school",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_interests": ["NLP", "machine learning"],
            "progress": [],
        }

        result = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": "professor-e2e"}},
        )

        # Verify all steps completed
        progress = result.get("progress", [])
        assert "load_professor_context" in progress
        assert "query_openalex" in progress
        assert "enrich_semantic_scholar" in progress
        assert "synthesize_rank" in progress
        assert "stage_professor_matches" in progress
        assert "promote_professor_matches" in progress

        # Verify candidates were found
        assert len(result.get("enriched_candidates", [])) == 1
