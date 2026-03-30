"""Tests for the Redis inflight semaphore and DossierService cap enforcement."""
import uuid
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests: acquire_inflight / release_inflight primitives
# ---------------------------------------------------------------------------

class TestInflightPrimitives:

    @pytest.fixture()
    def mock_redis(self):
        return MagicMock()

    def test_acquire_under_cap_returns_acquired_true(self, mock_redis):
        """When INCR succeeds (below cap), acquired=True."""
        mock_redis.eval.return_value = [1, 3]  # allowed=1, current=3

        with (
            patch("src.pipeline.redis_keyspace.inflight._get_redis", return_value=mock_redis),
        ):
            from src.pipeline.redis_keyspace.inflight import acquire_inflight, InflightResult
            result = acquire_inflight("dossier", max_concurrent=10)

        assert result.acquired is True
        assert result.current == 3
        assert result.maximum == 10

    def test_acquire_at_cap_returns_acquired_false(self, mock_redis):
        """When counter is at cap, acquired=False."""
        mock_redis.eval.return_value = [0, 10]  # allowed=0, current=10

        with patch("src.pipeline.redis_keyspace.inflight._get_redis", return_value=mock_redis):
            from src.pipeline.redis_keyspace.inflight import acquire_inflight
            result = acquire_inflight("dossier", max_concurrent=10)

        assert result.acquired is False
        assert result.current == 10

    def test_release_decrements_counter(self, mock_redis):
        """release_inflight should call INFLIGHT_DECR and return new count."""
        mock_redis.eval.return_value = 7

        with patch("src.pipeline.redis_keyspace.inflight._get_redis", return_value=mock_redis):
            from src.pipeline.redis_keyspace.inflight import release_inflight
            result = release_inflight("dossier")

        assert result == 7
        mock_redis.eval.assert_called_once()

    def test_acquire_fails_open_on_redis_error(self):
        """When Redis raises, acquire_inflight returns acquired=True (fail open)."""
        broken = MagicMock()
        broken.eval.side_effect = ConnectionError("Redis down")

        with patch("src.pipeline.redis_keyspace.inflight._get_redis", return_value=broken):
            from src.pipeline.redis_keyspace.inflight import acquire_inflight
            result = acquire_inflight("dossier", max_concurrent=5)

        assert result.acquired is True

    def test_release_handles_redis_error_gracefully(self):
        """release_inflight should not raise on Redis error — returns 0."""
        broken = MagicMock()
        broken.eval.side_effect = RuntimeError("Redis gone")

        with patch("src.pipeline.redis_keyspace.inflight._get_redis", return_value=broken):
            from src.pipeline.redis_keyspace.inflight import release_inflight
            result = release_inflight("dossier")

        assert result == 0


# ---------------------------------------------------------------------------
# Tests: DossierService integration
# ---------------------------------------------------------------------------

class TestDossierServiceInflightCap:
    """Tests for the inflight cap check inside DossierService._request()."""

    def _make_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def _make_repo(self):
        repo = MagicMock()
        repo.find_in_progress.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        repo.create_job.return_value = mock_job

        return repo, mock_job

    def test_returns_queued_cap_exceeded_when_cap_full(self):
        """DossierService should return queued_cap_exceeded when inflight cap reached."""
        from src.pipeline.redis_keyspace.inflight import InflightResult

        cap_exceeded = InflightResult(acquired=False, current=10, maximum=10)

        mock_settings = MagicMock()
        mock_settings.max_concurrent_dossier_jobs = 10

        repo, mock_job = self._make_repo()

        # Patch quota to allow, dedup to show no in-progress, cap to be full
        with (
            patch("src.services.dossier_service.check_and_increment_quota") as mock_quota,
            patch("src.services.dossier_service.JobRepository", return_value=repo),
            patch("src.services.dossier_service.acquire_inflight", return_value=cap_exceeded),
        ):
            mock_quota.return_value = MagicMock(allowed=True)

            from src.services.dossier_service import DossierService
            db = self._make_db()

            with patch("src.services.dossier_service._settings", mock_settings):
                service = DossierService(db)
                result = service.request_school_dossier(
                    school_id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                )

        assert result.status == "queued_cap_exceeded"
        assert result.job is not None
        assert result.message is not None
        assert "capacity" in result.message.lower()

    def test_returns_enqueued_when_cap_has_space(self):
        """When inflight cap not reached, job should be enqueued normally."""
        from src.pipeline.redis_keyspace.inflight import InflightResult

        cap_ok = InflightResult(acquired=True, current=3, maximum=10)

        mock_settings = MagicMock()
        mock_settings.max_concurrent_dossier_jobs = 10

        repo, mock_job = self._make_repo()

        with (
            patch("src.services.dossier_service.check_and_increment_quota") as mock_quota,
            patch("src.services.dossier_service.JobRepository", return_value=repo),
            patch("src.services.dossier_service.acquire_inflight", return_value=cap_ok),
            patch("src.services.dossier_service.DossierService._dispatch"),
        ):
            mock_quota.return_value = MagicMock(allowed=True)

            from src.services.dossier_service import DossierService
            db = self._make_db()

            with patch("src.services.dossier_service._settings", mock_settings):
                service = DossierService(db)
                result = service.request_school_dossier(
                    school_id=str(uuid.uuid4()),
                    user_id=str(uuid.uuid4()),
                )

        assert result.status == "enqueued"
