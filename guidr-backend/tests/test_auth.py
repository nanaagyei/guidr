"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db import Base, engine
from src.models.user import User
from src.utils.password import hash_password, verify_password
from src.utils.jwt import create_access_token, decode_access_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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


def test_register_user():
    """Test user registration."""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "password_hash" not in data


def test_register_duplicate_email():
    """Test registration with duplicate email."""
    # Register first user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Try to register again
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_short_password():
    """Test registration with short password."""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "short"
        }
    )
    
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


def test_login_success():
    """Test successful login."""
    # Register user first
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Login
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 200
    assert "session" in response.cookies
    data = response.json()
    assert data["email"] == "test@example.com"


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]

