"""Funding and documents APIs are not reachable unless their feature flags are on."""
import importlib
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth():
    """Mock authenticated user."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user


def _client_for(app, mock_auth, mock_db):
    from src.db import get_db
    from src.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_auth
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)


@pytest.fixture
def rate_limit_redis():
    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        yield


@pytest.fixture
def default_app(mock_auth, rate_limit_redis):
    """The app as imported with default settings (both flags off)."""
    from src.main import app

    mock_db = MagicMock()
    yield _client_for(app, mock_auth, mock_db), mock_db
    app.dependency_overrides.clear()


@pytest.fixture
def app_with_flags(mock_auth, rate_limit_redis):
    """Rebuild ``src.main`` with both flags on; restore the default app afterwards.

    Routers are included at import time, so the module is reloaded with the
    settings patched, then reloaded again with defaults so other tests are unaffected.
    """
    import src.main as main_mod
    from src.config import settings

    mock_db = MagicMock()
    with patch.object(settings, "enable_funding_api", True), \
         patch.object(settings, "enable_documents_api", True):
        reloaded = importlib.reload(main_mod)
        client = _client_for(reloaded.app, mock_auth, mock_db)
        try:
            yield client, mock_db
        finally:
            reloaded.app.dependency_overrides.clear()
    importlib.reload(main_mod)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/funding"),
        ("get", "/documents"),
        ("post", "/documents/upload-url"),
        ("post", f"/dossiers/schools/{uuid.uuid4()}/funding/research"),
    ],
)
def test_gated_endpoints_return_404_by_default(default_app, method, path):
    client, _ = default_app

    response = getattr(client, method)(path, json={}) if method == "post" else client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/funding", "/documents"])
def test_list_endpoints_routed_when_flag_on(app_with_flags, path):
    client, mock_db = app_with_flags
    mock_db.query.return_value = MagicMock()

    response = client.get(path)

    assert response.status_code != 404


def test_profile_unlock_reports_funding_off():
    from src.utils.profile_completion import calculate_profile_completion

    profile = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 1
    db.query.return_value.filter.return_value.first.return_value = None

    result = calculate_profile_completion(profile, db)

    assert result["unlocks"]["funding"] is False


def test_save_recommendation_skips_funding_job_when_flag_off(default_app, mock_auth):
    client, mock_db = default_app

    result = MagicMock()
    result.id = uuid.uuid4()
    result.school_name = "Example University"
    result.program_name = "PhD Example"
    session = MagicMock()
    institution = MagicMock()
    institution.id = uuid.uuid4()
    program = MagicMock()
    program.id = uuid.uuid4()

    profile = MagicMock()
    profile.research_areas = ["machine learning"]

    # Query order in save_recommendation: result, session, existing saved,
    # institution (exact match), program, profile (for professor matching).
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        result, session, None, institution, program, profile,
    ]

    with patch("src.services.dossier_service.DossierService") as MockService:
        svc = MockService.return_value
        svc.request_school_dossier.return_value.job = None
        svc.request_professor_matches.return_value.job = None

        response = client.post(f"/recommendations/results/{result.id}/save")

    assert response.status_code == 200, response.text
    svc.request_school_dossier.assert_called_once()
    svc.request_professor_matches.assert_called_once()
    svc.request_funding_dossier.assert_not_called()
