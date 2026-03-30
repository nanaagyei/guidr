"""Unit tests for professor match graph nodes with mocked APIs."""
import pytest
from unittest.mock import patch, MagicMock


class TestLoadProfessorContext:
    """Tests for load_professor_context node."""

    @patch("src.pipeline.orchestrator.professor_nodes._get_db")
    def test_loads_institution_name(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inst = MagicMock()
        mock_inst.name = "Stanford University"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_inst

        from src.pipeline.orchestrator.professor_nodes import load_professor_context

        state = {
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_interests": ["machine learning"],
            "progress": [],
        }
        result = load_professor_context(state)

        assert result["institution_name"] == "Stanford University"
        assert "machine learning" in result["user_interests"]

    @patch("src.pipeline.orchestrator.professor_nodes._get_db")
    def test_loads_user_interests_from_profile(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_inst = MagicMock()
        mock_inst.name = "MIT"
        mock_profile = MagicMock()
        mock_profile.primary_field_of_study = "Computer Science"
        mock_profile.secondary_fields = ["AI", "Robotics"]

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_inst, mock_profile
        ]

        from src.pipeline.orchestrator.professor_nodes import load_professor_context

        state = {
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "user_interests": [],
            "progress": [],
        }
        result = load_professor_context(state)

        assert "Computer Science" in result["user_interests"]
        assert "AI" in result["user_interests"]


class TestQueryOpenAlex:
    """Tests for query_openalex node."""

    @patch("src.pipeline.clients.openalex.OpenAlexClient")
    def test_returns_candidates(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        mock_instance.search_authors.return_value = [
            {
                "id": "A123",
                "display_name": "Jane Smith",
                "works_count": 80,
                "cited_by_count": 3000,
                "last_known_institutions": [{"display_name": "MIT"}],
                "topics": [{"display_name": "NLP"}],
            },
            {
                "id": "A456",
                "display_name": "John Doe",
                "works_count": 45,
                "cited_by_count": 1500,
                "last_known_institutions": [{"display_name": "MIT"}],
                "topics": [],
            },
        ]

        from src.pipeline.orchestrator.professor_nodes import query_openalex

        state = {
            "institution_name": "MIT",
            "user_interests": ["NLP", "machine learning"],
            "progress": [],
        }
        result = query_openalex(state)

        assert len(result["openalex_candidates"]) == 2
        assert result["openalex_candidates"][0]["name"] == "Jane Smith"
        assert result["openalex_candidates"][0]["openalex_id"] == "A123"

    @patch("src.pipeline.clients.openalex.OpenAlexClient")
    def test_handles_empty_results(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.search_authors.return_value = []

        from src.pipeline.orchestrator.professor_nodes import query_openalex

        state = {
            "institution_name": "Unknown Uni",
            "user_interests": [],
            "progress": [],
        }
        result = query_openalex(state)

        assert result["openalex_candidates"] == []


class TestEnrichSemanticScholar:
    """Tests for enrich_semantic_scholar node."""

    @patch("src.pipeline.clients.semantic_scholar.SemanticScholarClient")
    def test_enriches_candidates(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        mock_instance.search_author.return_value = [
            {
                "authorId": "S2_123",
                "name": "Jane Smith",
                "hIndex": 35,
                "paperCount": 80,
                "citationCount": 3000,
            }
        ]
        mock_instance.get_author_papers.return_value = [
            {"title": "Deep NLP", "year": 2024, "citationCount": 25}
        ]

        from src.pipeline.orchestrator.professor_nodes import enrich_semantic_scholar

        state = {
            "openalex_candidates": [
                {"openalex_id": "A123", "name": "Jane Smith"}
            ],
            "progress": [],
        }
        result = enrich_semantic_scholar(state)

        assert len(result["enriched_candidates"]) == 1
        enriched = result["enriched_candidates"][0]
        assert enriched["semantic_scholar_id"] == "S2_123"
        assert enriched["h_index"] == 35
        assert len(enriched["recent_papers"]) == 1

    @patch("src.pipeline.clients.semantic_scholar.SemanticScholarClient")
    def test_handles_no_match(self, MockClient):
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.search_author.return_value = []

        from src.pipeline.orchestrator.professor_nodes import enrich_semantic_scholar

        state = {
            "openalex_candidates": [
                {"openalex_id": "A999", "name": "Unknown Person"}
            ],
            "progress": [],
        }
        result = enrich_semantic_scholar(state)

        assert len(result["enriched_candidates"]) == 1
        assert "semantic_scholar_id" not in result["enriched_candidates"][0]


class TestStageProfessorMatches:
    """Tests for stage_professor_matches node."""

    @patch("src.pipeline.orchestrator.professor_nodes._get_db")
    def test_creates_cache_entry(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from src.pipeline.orchestrator.professor_nodes import stage_professor_matches

        state = {
            "ranked_professors": [
                {"name": "Jane Smith", "openalex_id": "A123", "relevance_score": 90}
            ],
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "confidence": 0.80,
            "synthesis_citations": [],
            "synthesis_evidence_map": {},
            "progress": [],
        }
        result = stage_professor_matches(state)

        assert "stage_professor_matches" in result["progress"]
        mock_db.commit.assert_called_once()
