"""API tests for GET/PUT /profile/ai-research-consent."""
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.db import get_db
    from src.dependencies.auth import get_current_user
    from src.main import app

    user = MagicMock()
    user.id = uuid.uuid4()
    profile = SimpleNamespace(user_id=user.id, ai_research_consent_at=None)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = profile

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        yield TestClient(app), mock_db, profile

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_defaults_to_no_consent(client):
    test_client, _, _ = client
    resp = test_client.get("/profile/ai-research-consent")
    assert resp.status_code == 200
    assert resp.json() == {"consented": False, "consented_at": None}


def test_grant_records_timestamp(client):
    test_client, mock_db, profile = client
    resp = test_client.put("/profile/ai-research-consent", json={"consent": True})
    assert resp.status_code == 200
    assert resp.json()["consented"] is True
    assert isinstance(profile.ai_research_consent_at, datetime)
    mock_db.commit.assert_called()


def test_grant_keeps_original_timestamp(client):
    test_client, _, profile = client
    first = datetime(2026, 1, 1)
    profile.ai_research_consent_at = first
    test_client.put("/profile/ai-research-consent", json={"consent": True})
    assert profile.ai_research_consent_at == first


def test_withdraw_clears_timestamp(client):
    test_client, _, profile = client
    profile.ai_research_consent_at = datetime(2026, 1, 1)
    resp = test_client.put("/profile/ai-research-consent", json={"consent": False})
    assert resp.json() == {"consented": False, "consented_at": None}
    assert profile.ai_research_consent_at is None


def test_profile_update_cannot_set_consent(client):
    """Consent is only recorded through the dedicated endpoint."""
    from src.schemas.profile import UserProfileUpdate

    data = UserProfileUpdate(ai_research_consent_at="2026-01-01T00:00:00").model_dump(
        exclude_unset=True
    )
    assert "ai_research_consent_at" not in data
