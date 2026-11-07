"""Research endpoints fail closed in production when no real provider is configured."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_ID = str(uuid.uuid4())

GUARDED_ENDPOINTS = [
    "/recommendations/run",
    "/recommendations/request",
    f"/recommendations/results/{_ID}/save",
    f"/dossiers/schools/{_ID}/research",
    f"/dossiers/schools/{_ID}/professors/match",
    f"/dossiers/schools/{_ID}/funding/research",
    "/internal/research/run",
    "/pipeline/enrich",
    "/pipeline/enrich/shortlist",
    "/pipeline/admin/refresh",
    f"/pipeline/admin/jobs/{_ID}/rerun",
]


@pytest.fixture
def mock_auth():
    """Mock authenticated user."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user


@pytest.fixture
def client(mock_auth):
    """Test client with auth and DB overridden, rate limiting mocked."""
    from src.db import get_db
    from src.dependencies.auth import get_current_user
    from src.main import app

    mock_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_auth
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        yield TestClient(app), mock_db

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def production_without_provider():
    """Patch settings to production with no research provider keys."""
    from src.config import settings

    # enable_funding_api is on so the funding endpoint reaches the research guard.
    with patch.object(settings, "env", "production"), \
         patch.object(settings, "enable_funding_api", True), \
         patch.object(settings, "perplexity_api_key", None), \
         patch.object(settings, "open_deep_research_api_key", None), \
         patch.object(settings, "open_deep_research_base_url", None):
        yield


@pytest.mark.parametrize("path", GUARDED_ENDPOINTS)
def test_guarded_endpoint_returns_503_and_writes_nothing(
    client, production_without_provider, path
):
    test_client, mock_db = client

    response = test_client.post(path, json={})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RESEARCH_UNAVAILABLE"
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_guard_allows_request_when_provider_configured(client):
    """With a provider key in production the guard lets the request through."""
    from src.config import settings

    test_client, _ = client
    with patch.object(settings, "env", "production"), \
         patch.object(settings, "perplexity_api_key", "pplx-test"):
        response = test_client.post(f"/dossiers/schools/{_ID}/research", json={})

    assert response.status_code != 503
