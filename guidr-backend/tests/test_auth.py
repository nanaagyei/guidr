"""Tests for authentication endpoints and utilities."""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.utils.password import hash_password, verify_password
from src.utils.jwt import create_access_token, decode_access_token


# ---------------------------------------------------------------------------
# Pure utility tests (no DB needed)
# ---------------------------------------------------------------------------


def test_hash_and_verify_password():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_jwt():
    """Test JWT creation and decoding."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    email = "test@example.com"
    role = "user"

    token = create_access_token(user_id, email, role)
    assert token is not None

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["role"] == role


# ---------------------------------------------------------------------------
# Endpoint tests (mocked DB)
# ---------------------------------------------------------------------------


def _make_mock_user(
    email="test@example.com",
    full_name="Test User",
    password="testpassword123",
    role="user",
    is_deleted=False,
):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.full_name = full_name
    user.password_hash = hash_password(password)
    user.role = role
    user.is_deleted = is_deleted
    user.created_at = datetime(2026, 1, 1)
    user.last_login_at = None
    return user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Test client with get_db overridden to return a mock session."""
    from src.db import get_db
    from src.main import app

    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


class TestRegister:
    """Tests for POST /auth/register."""

    def test_register_user(self, client, mock_db):
        """Successful registration with valid 2FA code."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def _fake_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2026, 1, 1)
            obj.role = "user"

        mock_db.refresh = _fake_refresh

        mock_2fa = MagicMock()
        with patch(
            "src.routes.auth.verify_2fa_code", return_value=(True, mock_2fa)
        ):
            response = client.post(
                "/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "testpassword123",
                    "full_name": "Test User",
                    "verification_code": "123456",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client, mock_db):
        """Registration with existing email returns 400."""
        existing_user = _make_mock_user()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User",
                "verification_code": "123456",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_short_password(self, client, mock_db):
        """Short password is rejected by Pydantic validation (422)."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "full_name": "Test User",
                "verification_code": "123456",
            },
        )

        # Pydantic min_length=8 on password raises 422 before route logic runs
        assert response.status_code == 422

    def test_register_missing_verification_code(self, client, mock_db):
        """Registration without verification code returns 400."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 400
        assert "Verification code is required" in response.json()["detail"]


class TestLogin:
    """Tests for POST /auth/login."""

    def test_login_success(self, client, mock_db):
        """Successful login with valid credentials."""
        existing_user = _make_mock_user()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        assert "session" in response.cookies
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client, mock_db):
        """Login with non-existent email returns 401."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_login_wrong_password(self, client, mock_db):
        """Login with wrong password returns 401."""
        existing_user = _make_mock_user(password="correctpassword1")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword1",
            },
        )

        assert response.status_code == 401

    def test_login_remember_me(self, client, mock_db):
        """Login with remember_me sets 30-day cookie."""
        existing_user = _make_mock_user()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "remember_me": True,
            },
        )

        assert response.status_code == 200
        assert "session" in response.cookies
