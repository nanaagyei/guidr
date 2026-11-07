"""POST /essays/{id}/review is not available yet."""
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


def test_review_owned_essay_returns_501(client, mock_auth):
    test_client, mock_db = client
    essay = MagicMock()
    essay.user_id = mock_auth.id
    mock_db.query.return_value.filter.return_value.first.return_value = essay

    response = test_client.post(f"/essays/{uuid.uuid4()}/review")

    assert response.status_code == 501
    assert response.json() == {"detail": "Essay review is not available yet"}
    mock_db.add.assert_not_called()


def test_review_unowned_essay_returns_404(client):
    test_client, mock_db = client
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = test_client.post(f"/essays/{uuid.uuid4()}/review")

    assert response.status_code == 404


def test_worker_cannot_write_canned_review():
    from src.workers.essay_reviewer import review_essay

    with pytest.raises(NotImplementedError):
        review_essay(str(uuid.uuid4()))
