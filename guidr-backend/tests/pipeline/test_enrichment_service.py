"""Unit tests for EnrichmentService: cache hit, quota, dedup, dispatch paths."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import uuid


class TestEnrichmentService:
    """Tests for EnrichmentService."""

    def _make_service(self, mock_db=None):
        if mock_db is None:
            mock_db = MagicMock()
        from src.services import enrichment_service as mod
        with patch.object(mod, "JobRepository"):
            from src.services.enrichment_service import EnrichmentService
            return EnrichmentService(mock_db), mod

    # ── cache hit ──────────────────────────────────────────────────────

    def test_cache_hit_returns_cached_and_bumps_hit_count(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        mock_cache = MagicMock()
        mock_cache.expires_at = datetime.utcnow() + timedelta(days=10)
        mock_cache.confidence = Decimal("0.90")
        mock_cache.value_json = {"description": "Great school"}
        mock_cache.hit_count = 3
        mock_cache.last_hit_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_cache

        with patch.object(mod, "check_and_increment_quota") as mock_quota:
            result = service.enrich_entity(
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
            )

        assert result.status == "cache_hit"
        assert result.cache_entry is mock_cache
        assert mock_cache.hit_count == 4  # Bumped from 3 to 4

    # ── force refresh ──────────────────────────────────────────────────

    def test_force_refresh_bypasses_cache(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job
        service.repo.find_in_progress.return_value = None

        with patch.object(mod, "check_and_increment_quota") as mock_quota:
            mock_quota.return_value = MagicMock(allowed=True)
            with patch.object(service, "_dispatch"):
                result = service.enrich_entity(
                    entity_kind="school",
                    entity_id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                    force_refresh=True,
                )

        assert result.status == "enqueued"

    # ── quota exceeded ─────────────────────────────────────────────────

    def test_quota_exceeded(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch.object(mod, "check_and_increment_quota") as mock_quota:
            mock_quota.return_value = MagicMock(allowed=False, limit=10)

            result = service.enrich_entity(
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
            )

        assert result.status == "quota_exceeded"
        assert "limit reached" in result.message

    # ── dedup ──────────────────────────────────────────────────────────

    def test_dedup_in_progress(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.find_in_progress.return_value = mock_job

        with patch.object(mod, "check_and_increment_quota") as mock_quota:
            mock_quota.return_value = MagicMock(allowed=True)

            result = service.enrich_entity(
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
            )

        assert result.status == "dedup_in_progress"
        assert result.job is mock_job
        assert "already in progress" in result.message

    # ── happy path ─────────────────────────────────────────────────────

    def test_create_and_dispatch_happy_path(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None
        service.repo.find_in_progress.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job

        with patch.object(mod, "check_and_increment_quota") as mock_quota:
            mock_quota.return_value = MagicMock(allowed=True)
            with patch.object(service, "_dispatch") as mock_dispatch:
                result = service.enrich_entity(
                    entity_kind="school",
                    entity_id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                )

        assert result.status == "enqueued"
        assert result.job is mock_job
        mock_dispatch.assert_called_once_with(mock_job)

    # ── get_cache_status stale ─────────────────────────────────────────

    def test_get_cache_status_stale(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        # Expired cache entry
        mock_cache = MagicMock()
        mock_cache.expires_at = datetime.utcnow() - timedelta(days=1)
        mock_cache.confidence = Decimal("0.75")
        mock_cache.computed_at = datetime.utcnow() - timedelta(days=35)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_cache

        status = service.get_cache_status(
            entity_kind="school",
            entity_id=str(uuid.uuid4()),
        )

        assert status["has_cache"] is True
        assert status["is_stale"] is True

    # ── get_cache_value ────────────────────────────────────────────────

    def test_get_cache_value_bumps_hit_count(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        mock_cache = MagicMock()
        mock_cache.value_json = {"description": "Test"}
        mock_cache.hit_count = 2
        mock_cache.last_hit_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_cache

        value = service.get_cache_value(
            entity_kind="school",
            entity_id=str(uuid.uuid4()),
        )

        assert value == {"description": "Test"}
        assert mock_cache.hit_count == 3
        mock_db.flush.assert_called()

    # ── dispatch routing ───────────────────────────────────────────────

    def test_dispatch_routes_dossier_types(self):
        mock_db = MagicMock()
        service, mod = self._make_service(mock_db)

        # Test dossier job type routes to dossier task
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.job_type = "dossier"
        mock_job.entity_id = uuid.uuid4()
        mock_job.entity_kind = "school"

        from src.pipeline.tasks import dossier_tasks as dtasks_mod

        with patch.object(dtasks_mod, "run_dossier_pipeline", create=True) as mock_dossier_task:
            service._dispatch(mock_job)
            mock_dossier_task.delay.assert_called_once_with(str(mock_job.id))

        # Test professor_match routes to professor_match task
        mock_job.job_type = "professor_match"

        with patch.object(dtasks_mod, "run_professor_match_pipeline", create=True) as mock_prof_task:
            service._dispatch(mock_job)
            mock_prof_task.delay.assert_called_once_with(str(mock_job.id))
