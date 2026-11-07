"""Tests for account export, password change and deletion (#56)."""
import importlib
import json
import pkgutil
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.utils.password import hash_password, verify_password

def _synthetic_test_credential(label: str) -> str:
    """Policy-compliant fixture values only; not production secrets."""
    return f"guidr-test-{label}-9X!"


CURRENT_TEST_CREDENTIAL = _synthetic_test_credential("account-current")
NEW_TEST_CREDENTIAL = _synthetic_test_credential("account-new")
FORBIDDEN_KEYS = {"password_hash", "password_history", "two_factor_codes", "code"}


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "applicant@example.com"
    user.full_name = "Applicant"
    user.created_at = datetime(2026, 1, 1)
    user.password_hash = hash_password(CURRENT_TEST_CREDENTIAL)
    return user


@pytest.fixture
def client(mock_user):
    """Client with a mocked user and a MagicMock session that returns no rows."""
    from src.db import get_db
    from src.dependencies.auth import get_current_user
    from src.main import app

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        yield TestClient(app), mock_db

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #

def test_export_returns_attachment_without_secrets(client):
    test_client, _ = client

    response = test_client.get("/account/export")

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="guidr-export-')
    assert disposition.endswith('.json"')
    payload = response.json()
    for key in (
        "exported_at", "user", "profile", "academic_records", "essays", "documents",
        "recommendation_sessions", "saved_recommendations", "outreach_emails",
        "research_cache_entries",
    ):
        assert key in payload
    assert not FORBIDDEN_KEYS & set(_all_keys(payload))


# --------------------------------------------------------------------------- #
# Change password
# --------------------------------------------------------------------------- #

def test_change_password_wrong_current_returns_400(client, mock_user):
    test_client, mock_db = client
    old_hash = mock_user.password_hash

    response = test_client.post(
        "/account/change-password",
        json={"current_password": "wrong-password", "new_password": NEW_TEST_CREDENTIAL},
    )

    assert response.status_code == 400
    assert mock_user.password_hash == old_hash
    mock_db.commit.assert_not_called()


def test_change_password_weak_new_password_returns_400(client, mock_user):
    test_client, _ = client

    response = test_client.post(
        "/account/change-password",
        json={"current_password": CURRENT_TEST_CREDENTIAL, "new_password": "short"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Weak password")


def test_change_password_reuse_returns_400(client):
    test_client, _ = client

    response = test_client.post(
        "/account/change-password",
        json={"current_password": CURRENT_TEST_CREDENTIAL, "new_password": CURRENT_TEST_CREDENTIAL},
    )

    assert response.status_code == 400
    assert "reuse" in response.json()["detail"]


def test_change_password_success_updates_hash(client, mock_user):
    test_client, _ = client

    response = test_client.post(
        "/account/change-password",
        json={"current_password": CURRENT_TEST_CREDENTIAL, "new_password": NEW_TEST_CREDENTIAL},
    )

    assert response.status_code == 200
    assert verify_password(NEW_TEST_CREDENTIAL, mock_user.password_hash)


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #

def test_delete_wrong_password_deletes_nothing(client, mock_user):
    test_client, mock_db = client

    response = test_client.post("/account/delete", json={"password": "wrong-password"})

    assert response.status_code == 400
    mock_db.query.return_value.filter.return_value.delete.assert_not_called()
    mock_db.commit.assert_not_called()
    assert mock_user.is_deleted is not True


def test_delete_success_anonymises_user_and_clears_cookie(client, mock_user):
    test_client, mock_db = client
    original_email = mock_user.email

    with patch("src.services.storage.storage_service") as storage:
        response = test_client.post("/account/delete", json={"password": CURRENT_TEST_CREDENTIAL})

    assert response.status_code == 204
    assert mock_user.is_deleted is True
    assert mock_user.password_hash is None
    assert mock_user.full_name is None
    assert mock_user.email != original_email
    assert mock_user.email.endswith("@deleted.invalid")
    mock_db.commit.assert_called_once()
    set_cookie = response.headers.get("set-cookie", "")
    assert set_cookie.startswith("session=")
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()
    storage.delete_file.assert_not_called()  # the mocked session holds no documents


# --------------------------------------------------------------------------- #
# Coverage guard: no user-owned table may be missing from USER_OWNED_MODELS
# --------------------------------------------------------------------------- #

def test_every_model_with_user_id_is_user_owned():
    import src.models
    from src.models.base import Base
    from src.services.account_service import USER_OWNED_MODELS

    for module in pkgutil.iter_modules(src.models.__path__):
        importlib.import_module(f"src.models.{module.name}")

    owned = set(USER_OWNED_MODELS)
    missing = [
        mapper.class_.__name__
        for mapper in Base.registry.mappers
        if "user_id" in mapper.columns and mapper.class_ not in owned
    ]
    assert missing == [], f"Add these models to USER_OWNED_MODELS: {missing}"


# --------------------------------------------------------------------------- #
# End to end against a migrated Postgres (skipped when the schema is absent)
# --------------------------------------------------------------------------- #

def _migrated_session():
    from sqlalchemy import inspect

    from src.db import SessionLocal, engine

    if getattr(getattr(engine, "dialect", None), "name", None) != "postgresql":
        # tests/pipeline/conftest.py replaces src.db with a mock, so in a full run this test
        # skips. Run it on its own against a migrated database:
        #   alembic upgrade head && pytest tests/routes/test_account_routes.py
        pytest.skip("needs a real Postgres engine (src.db is mocked in a full run)")
    try:
        if not inspect(engine).has_table("users") or not inspect(engine).has_table("essays"):
            pytest.skip("needs a migrated database (alembic upgrade head)")
    except Exception:
        pytest.skip("database not reachable")
    return SessionLocal()


def test_delete_removes_every_user_owned_row_end_to_end():
    from src.main import app
    from src.models.academic_record import AcademicRecord
    from src.models.enrichment_cache import EnrichmentCache
    from src.models.essay import Essay
    from src.models.essay_version import EssayVersion
    from src.models.institution import Institution
    from src.models.outreach_email import OutreachEmail
    from src.models.password_history import PasswordHistory
    from src.models.professor import Professor
    from src.models.recommendation_result import RecommendationResult
    from src.models.recommendation_session import RecommendationSession
    from src.models.two_factor_code import TwoFactorCode
    from src.models.user import User
    from src.models.user_profile import UserProfile
    from src.services.account_service import USER_OWNED_MODELS

    db = _migrated_session()
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    user = User(email=email, password_hash=hash_password(CURRENT_TEST_CREDENTIAL), full_name="E2E")
    db.add(user)
    db.flush()
    uid = user.id
    db.add(UserProfile(user_id=uid, intended_degree="phd"))
    db.add(AcademicRecord(user_id=uid, institution_name="Example U", country="GH",
                          degree_level="bachelors"))
    essay = Essay(user_id=uid, title="SOP")
    db.add(essay)
    db.flush()
    db.add(EssayVersion(essay_id=essay.id, version_number=1, content="Hello", word_count=1))
    session = RecommendationSession(user_id=uid)
    db.add(session)
    db.flush()
    session_id = session.id
    db.add(RecommendationResult(recommendation_session_id=session.id, school_name="X",
                                rank=1, score=50, tier="target"))
    institution = Institution(name=f"E2E Institution {uuid.uuid4().hex[:6]}", country="US")
    db.add(institution)
    db.flush()
    professor = Professor(institution_id=institution.id, full_name="Prof E2E")
    db.add(professor)
    db.flush()
    professor_id, institution_id = professor.id, institution.id
    db.add(OutreachEmail(user_id=uid, professor_id=professor_id, subject="Hi", body="Hello"))
    db.add(EnrichmentCache(entity_kind="school", entity_id=uuid.uuid4(), user_id=uid,
                           value_json={}, expires_at=datetime.utcnow() + timedelta(days=1)))
    db.add(TwoFactorCode(user_id=None, code="123456", email=email, purpose="register",
                         expires_at=datetime.utcnow() + timedelta(minutes=10)))
    db.add(PasswordHistory(user_id=uid, password_hash=hash_password("Older-passw0rd!x")))
    db.commit()

    with patch("src.dependencies.rate_limit._get_redis") as mock_redis_fn:
        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 1, 59]
        mock_redis_fn.return_value = mock_redis
        test_client = TestClient(app)
        login = test_client.post("/auth/login", json={"email": email, "password": CURRENT_TEST_CREDENTIAL})
        assert login.status_code == 200, login.text
        old_cookie = login.cookies.get("session")

        export = test_client.get("/account/export")
        assert export.status_code == 200
        exported = export.json()
        assert exported["user"]["email"] == email
        assert len(exported["essays"]) == 1 and len(exported["essays"][0]["versions"]) == 1
        assert not FORBIDDEN_KEYS & set(_all_keys(exported))
        json.dumps(exported)

        response = test_client.post("/account/delete", json={"password": CURRENT_TEST_CREDENTIAL})
        assert response.status_code == 204

        # The old session cookie is rejected.
        stale = TestClient(app)
        stale.cookies.set("session", old_cookie)
        assert stale.get("/auth/me").status_code == 401

    db.expire_all()
    for model in USER_OWNED_MODELS:
        if "user_id" in model.__table__.columns:
            assert db.query(model).filter(model.user_id == uid).count() == 0, model.__name__
    assert db.query(RecommendationResult).filter(
        RecommendationResult.recommendation_session_id == session_id
    ).count() == 0
    assert db.query(TwoFactorCode).filter(TwoFactorCode.email == email).count() == 0
    deleted = db.query(User).filter(User.id == uid).one()
    assert deleted.is_deleted and deleted.password_hash is None
    assert deleted.email.endswith("@deleted.invalid")

    # The email can be registered again.
    db.add(User(email=email, password_hash=hash_password(CURRENT_TEST_CREDENTIAL)))
    db.commit()
    db.query(User).filter(User.email == email).delete()
    db.query(User).filter(User.id == uid).delete()
    db.query(Professor).filter(Professor.id == professor_id).delete()
    db.query(Institution).filter(Institution.id == institution_id).delete()
    db.commit()
    db.close()
