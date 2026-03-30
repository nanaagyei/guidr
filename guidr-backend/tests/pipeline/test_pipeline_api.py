"""API tests for pipeline enrichment routes."""
import pytest
from unittest.mock import patch, MagicMock
import uuid

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def mock_auth():
    """Mock authenticated user."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    return mock_user


@pytest.fixture
def client(mock_auth):
    """Create test client with mocked auth and DB."""
    with patch("src.routes.pipeline.get_current_user", return_value=mock_auth):
        with patch("src.routes.pipeline.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            from src.main import app
            yield TestClient(app), mock_db


@pytest.fixture
def admin_client(mock_auth):
    """Create test client with mocked admin auth."""
    with patch("src.routes.pipeline.get_current_user", return_value=mock_auth):
        with patch("src.routes.pipeline.require_admin_user", return_value=mock_auth):
            with patch("src.routes.pipeline.get_db") as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db
                from src.main import app
                yield TestClient(app), mock_db


# ------------------------------------------------------------------
# POST /pipeline/enrich
# ------------------------------------------------------------------


class TestTriggerEnrichment:
    """Tests for POST /pipeline/enrich."""

    def test_trigger_enrichment_cache_hit(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_cache = MagicMock()
            mock_cache.value_json = {"description": "Top school"}
            mock_cache.confidence = 0.88
            mock_cache.computed_at = None
            mock_cache.expires_at = None

            mock_result = MagicMock()
            mock_result.status = "cache_hit"
            mock_result.message = "Fresh cache"
            mock_result.cache_entry = mock_cache
            mock_result.job = None

            mock_svc.enrich_entity.return_value = mock_result

            resp = test_client.post(
                "/pipeline/enrich",
                json={
                    "entity_kind": "school",
                    "entity_id": str(uuid.uuid4()),
                    "priority": "high",
                    "force_refresh": False,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cache_hit"
        assert data["cache"]["value"]["description"] == "Top school"

    def test_trigger_enrichment_enqueued(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_job = MagicMock()
            mock_job.id = uuid.uuid4()
            mock_job.status = "queued"
            mock_job.priority = "high"

            mock_result = MagicMock()
            mock_result.status = "enqueued"
            mock_result.message = "Job queued"
            mock_result.cache_entry = None
            mock_result.job = mock_job

            mock_svc.enrich_entity.return_value = mock_result

            resp = test_client.post(
                "/pipeline/enrich",
                json={
                    "entity_kind": "program",
                    "entity_id": str(uuid.uuid4()),
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"]["status"] == "queued"

    def test_trigger_enrichment_requires_auth(self):
        """Request without auth should be rejected."""
        from src.main import app

        test_client = TestClient(app)
        resp = test_client.post(
            "/pipeline/enrich",
            json={
                "entity_kind": "school",
                "entity_id": str(uuid.uuid4()),
            },
        )
        # Without the auth mock override the dependency will reject
        assert resp.status_code in (401, 403, 422)


# ------------------------------------------------------------------
# POST /pipeline/enrich/shortlist
# ------------------------------------------------------------------


class TestShortlistEnrichment:
    """Tests for POST /pipeline/enrich/shortlist."""

    def test_shortlist_multiple_entities(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc

            mock_result = MagicMock()
            mock_result.status = "enqueued"
            mock_result.message = "Queued"
            mock_result.cache_entry = None
            mock_job = MagicMock()
            mock_job.id = uuid.uuid4()
            mock_job.status = "queued"
            mock_job.priority = "bulk"
            mock_result.job = mock_job

            mock_svc.enrich_entity.return_value = mock_result

            resp = test_client.post(
                "/pipeline/enrich/shortlist",
                json={
                    "items": [
                        {"entity_kind": "school", "entity_id": str(uuid.uuid4())},
                        {"entity_kind": "program", "entity_id": str(uuid.uuid4())},
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(item["status"] == "enqueued" for item in data)


# ------------------------------------------------------------------
# GET /pipeline/cache/status
# ------------------------------------------------------------------


class TestCacheStatus:
    """Tests for GET /pipeline/cache/status."""

    def test_get_cache_status(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc
            mock_svc.get_cache_status.return_value = {
                "has_cache": True,
                "confidence": 0.85,
                "computed_at": None,
                "expires_at": None,
                "is_stale": False,
            }

            resp = test_client.get(
                "/pipeline/cache/status",
                params={"entity_kind": "school", "entity_id": str(uuid.uuid4())},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_cache"] is True
        assert data["confidence"] == 0.85


# ------------------------------------------------------------------
# GET /pipeline/cache/value
# ------------------------------------------------------------------


class TestCacheValue:
    """Tests for GET /pipeline/cache/value."""

    def test_get_cache_value_found(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc
            mock_svc.get_cache_value.return_value = {
                "description": "A top university",
                "acceptance_rate": 5.2,
            }

            resp = test_client.get(
                "/pipeline/cache/value",
                params={"entity_kind": "school", "entity_id": str(uuid.uuid4())},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "A top university"

    def test_get_cache_value_not_found_404(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.EnrichmentService") as MockService:
            mock_svc = MagicMock()
            MockService.return_value = mock_svc
            mock_svc.get_cache_value.return_value = None

            resp = test_client.get(
                "/pipeline/cache/value",
                params={"entity_kind": "school", "entity_id": str(uuid.uuid4())},
            )

        assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /pipeline/jobs/{job_id}
# ------------------------------------------------------------------


class TestJobStatus:
    """Tests for GET /pipeline/jobs/{job_id}."""

    def test_get_job_status_found(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.JobRepository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo

            mock_job = MagicMock()
            mock_job.id = uuid.uuid4()
            mock_job.status = "running"
            mock_job.output_json = {"progress": ["load_context", "fetch_page"], "confidence": 0.75}
            mock_job.error_message = None
            mock_job.queued_at = None
            mock_job.started_at = None
            mock_job.finished_at = None

            mock_repo.get_job.return_value = mock_job

            resp = test_client.get(f"/pipeline/jobs/{uuid.uuid4()}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "load_context" in data["progress"]

    def test_get_job_status_not_found_404(self, client, mock_auth):
        test_client, mock_db = client

        with patch("src.routes.pipeline.JobRepository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_job.return_value = None

            resp = test_client.get(f"/pipeline/jobs/{uuid.uuid4()}")

        assert resp.status_code == 404


# ------------------------------------------------------------------
# Admin endpoints
# ------------------------------------------------------------------


class TestAdminRefresh:
    """Tests for POST /pipeline/admin/refresh."""

    def test_admin_refresh_requires_admin(self):
        """Without admin mock the endpoint should reject."""
        from src.main import app

        test_client = TestClient(app)
        resp = test_client.post(
            "/pipeline/admin/refresh",
            json={
                "entity_kind": "school",
                "entity_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code in (401, 403, 422)


class TestAdminCancelJob:
    """Tests for POST /pipeline/admin/jobs/{job_id}/cancel."""

    def test_admin_cancel_job(self, admin_client, mock_auth):
        test_client, mock_db = admin_client

        with patch("src.routes.pipeline.JobRepository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.cancel_job.return_value = True

            job_id = str(uuid.uuid4())
            resp = test_client.post(f"/pipeline/admin/jobs/{job_id}/cancel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "canceled"


class TestAdminDomainHealth:
    """Tests for GET /pipeline/admin/domains."""

    def test_admin_domain_health(self, admin_client, mock_auth):
        test_client, mock_db = admin_client

        with patch(
            "src.routes.pipeline.DomainHealthService", create=True
        ) as mock_dhs_cls:
            # The route imports DomainHealthService inline, so patch at module level
            with patch(
                "src.pipeline.services.domain_health_service.DomainHealthService"
            ) as mock_dhs:
                mock_svc = MagicMock()
                mock_dhs.return_value = mock_svc
                mock_dhs_cls.return_value = mock_svc
                mock_svc.get_all_health.return_value = [
                    {"domain": "mit.edu", "status": "healthy", "error_count": 0},
                    {"domain": "blocked.edu", "status": "blocked", "error_count": 15},
                ]

                resp = test_client.get("/pipeline/admin/domains")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
