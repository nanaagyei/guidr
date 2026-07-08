"""API tests for dossier routes."""
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth():
    """Mock authenticated user."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user


@pytest.fixture
def client(mock_auth):
    """Create test client with proper FastAPI dependency overrides."""
    from src.db import get_db
    from src.dependencies.auth import get_current_user
    from src.main import app

    mock_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_auth
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        # Simulate: allowed=1, count=1, ttl=59
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        yield TestClient(app), mock_db

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


class TestSchoolDossierRoute:
    """Tests for POST /dossiers/schools/{id}/research."""

    def test_returns_enqueued(self, client, mock_auth):
        test_client, mock_db = client
        school_id = uuid.uuid4()

        with patch("src.routes.dossiers.DossierService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_job = MagicMock()
            mock_job.id = uuid.uuid4()

            mock_result = MagicMock()
            mock_result.status = "enqueued"
            mock_result.job = mock_job
            mock_result.cache_entry = None
            mock_result.message = None

            mock_svc.request_school_dossier.return_value = mock_result

            resp = test_client.post(f"/dossiers/schools/{school_id}/research")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "enqueued"
        assert "job_id" in data

    def test_returns_cache_hit(self, client, mock_auth):
        test_client, mock_db = client
        school_id = uuid.uuid4()

        with patch("src.routes.dossiers.DossierService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_cache = MagicMock()
            mock_cache.value_json = {"name": "MIT"}
            mock_cache.confidence = 0.90
            mock_cache.computed_at = MagicMock(
                isoformat=MagicMock(return_value="2026-03-01T00:00:00")
            )
            mock_cache.expires_at = MagicMock(
                isoformat=MagicMock(return_value="2026-03-31T00:00:00")
            )
            mock_cache.citations_json = [{"id": "c1", "url": "https://mit.edu"}]
            mock_cache.evidence_map_json = {"name": ["c1"]}

            mock_result = MagicMock()
            mock_result.status = "cache_hit"
            mock_result.job = None
            mock_result.cache_entry = mock_cache
            mock_result.message = None

            mock_svc.request_school_dossier.return_value = mock_result

            resp = test_client.post(f"/dossiers/schools/{school_id}/research")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cache_hit"
        assert data["cache"]["value_json"]["name"] == "MIT"


class TestProfessorMatchRoute:
    """Tests for POST /dossiers/schools/{id}/professors/match."""

    def test_accepts_research_interests(self, client, mock_auth):
        test_client, mock_db = client
        school_id = uuid.uuid4()

        with patch("src.routes.dossiers.DossierService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_result = MagicMock()
            mock_result.status = "enqueued"
            mock_result.job = MagicMock(id=uuid.uuid4())
            mock_result.cache_entry = None
            mock_result.message = None
            mock_svc.request_professor_matches.return_value = mock_result

            resp = test_client.post(
                f"/dossiers/schools/{school_id}/professors/match",
                json={"research_interests": ["NLP", "ML"], "department": "CS"},
            )

        assert resp.status_code == 200
        mock_svc.request_professor_matches.assert_called_once()
        call_kwargs = mock_svc.request_professor_matches.call_args
        assert call_kwargs.kwargs.get("research_interests") == ["NLP", "ML"]


class TestFundingDossierRoute:
    """Tests for POST /dossiers/schools/{id}/funding/research."""

    def test_returns_enqueued(self, client, mock_auth):
        test_client, mock_db = client
        school_id = uuid.uuid4()

        with patch("src.routes.dossiers.DossierService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_result = MagicMock()
            mock_result.status = "enqueued"
            mock_result.job = MagicMock(id=uuid.uuid4())
            mock_result.cache_entry = None
            mock_result.message = None
            mock_svc.request_funding_dossier.return_value = mock_result

            resp = test_client.post(f"/dossiers/schools/{school_id}/funding/research")

        assert resp.status_code == 200
        assert resp.json()["status"] == "enqueued"
