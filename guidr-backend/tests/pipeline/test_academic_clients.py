"""Unit tests for SemanticScholarClient and OpenAlexClient with mocked HTTP."""
import pytest
from unittest.mock import patch, MagicMock

import httpx


class TestSemanticScholarClient:
    """Tests for SemanticScholarClient."""

    def _make_client(self):
        with patch("src.pipeline.clients.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = "test-key"
            mock_settings.semantic_scholar_rps = 100.0
            mock_settings.redis_url = "redis://localhost:6379/0"
            from src.pipeline.clients.semantic_scholar import SemanticScholarClient
            return SemanticScholarClient(api_key="test-key")

    @patch("src.pipeline.clients.semantic_scholar.take_token")
    def test_search_author_success(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "authorId": "12345",
                    "name": "Jane Smith",
                    "affiliations": ["MIT"],
                    "hIndex": 42,
                    "paperCount": 150,
                    "citationCount": 8000,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            results = client.search_author("Jane Smith machine learning")

        assert len(results) == 1
        assert results[0]["authorId"] == "12345"
        assert results[0]["name"] == "Jane Smith"
        assert results[0]["hIndex"] == 42

    @patch("src.pipeline.clients.semantic_scholar.take_token")
    def test_search_author_empty_results(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            results = client.search_author("nonexistent researcher")

        assert results == []

    @patch("src.pipeline.clients.semantic_scholar.take_token")
    def test_get_author_not_found(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        with patch.object(client._client, "get", return_value=mock_response):
            result = client.get_author("nonexistent-id")

        assert result is None

    @patch("src.pipeline.clients.semantic_scholar.take_token")
    def test_get_author_papers_success(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Deep Learning for NLP",
                    "year": 2024,
                    "citationCount": 50,
                },
                {
                    "paperId": "def456",
                    "title": "Transformer Architectures",
                    "year": 2023,
                    "citationCount": 120,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            papers = client.get_author_papers("12345", limit=5)

        assert len(papers) == 2
        assert papers[0]["title"] == "Deep Learning for NLP"

    @patch("src.pipeline.clients.semantic_scholar.take_token")
    def test_http_error_returns_empty(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.object(client._client, "get", return_value=mock_response):
            results = client.search_author("test")

        assert results == []


class TestOpenAlexClient:
    """Tests for OpenAlexClient."""

    def _make_client(self):
        with patch("src.pipeline.clients.openalex.settings") as mock_settings:
            mock_settings.openalex_api_key = "test-key"
            mock_settings.openalex_rps = 100.0
            mock_settings.redis_url = "redis://localhost:6379/0"
            from src.pipeline.clients.openalex import OpenAlexClient
            return OpenAlexClient(api_key="test-key")

    @patch("src.pipeline.clients.openalex.take_token")
    def test_search_authors_success(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "A123",
                    "display_name": "John Doe",
                    "works_count": 80,
                    "cited_by_count": 3000,
                    "last_known_institutions": [
                        {"display_name": "Stanford University"}
                    ],
                    "topics": [{"display_name": "Machine Learning"}],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            results = client.search_authors("machine learning", affiliation_id="I123")

        assert len(results) == 1
        assert results[0]["display_name"] == "John Doe"

    @patch("src.pipeline.clients.openalex.take_token")
    def test_get_author_success(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "A123",
            "display_name": "John Doe",
            "works_count": 80,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            result = client.get_author("A123")

        assert result is not None
        assert result["display_name"] == "John Doe"

    @patch("src.pipeline.clients.openalex.take_token")
    def test_get_institution_not_found(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        with patch.object(client._client, "get", return_value=mock_response):
            result = client.get_institution("nonexistent")

        assert result is None

    @patch("src.pipeline.clients.openalex.take_token")
    def test_search_works_success(self, mock_take_token):
        mock_take_token.return_value = MagicMock(allowed=True)
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "W123",
                    "title": "A Study on NLP",
                    "publication_year": 2024,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_response):
            results = client.search_works("NLP", author_id="A123")

        assert len(results) == 1
        assert results[0]["title"] == "A Study on NLP"
