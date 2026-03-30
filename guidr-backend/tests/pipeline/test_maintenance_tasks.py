"""Unit tests for maintenance Celery tasks."""
import pytest
from unittest.mock import patch, MagicMock
import src.db as db_mod


# ------------------------------------------------------------------
# purge_expired_cache
# ------------------------------------------------------------------


class TestPurgeExpiredCache:
    """Tests for the purge_expired_cache task."""

    def test_purge_expired_cache_deletes_expired(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 5

        from src.pipeline.tasks.maintenance_tasks import purge_expired_cache

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            result = purge_expired_cache()

        assert result["purged"] == 5
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_purge_expired_cache_handles_error(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.side_effect = RuntimeError(
            "DB connection lost"
        )

        from src.pipeline.tasks.maintenance_tasks import purge_expired_cache

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            result = purge_expired_cache()

        assert "error" in result
        assert "DB connection lost" in result["error"]
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


# ------------------------------------------------------------------
# reset_domain_health
# ------------------------------------------------------------------


class TestResetDomainHealth:
    """Tests for the reset_domain_health task."""

    def test_reset_domain_health_delegates(self):
        mock_service = MagicMock()
        mock_service.reset_stale_blocks.return_value = 3

        from src.pipeline.services import domain_health_service as dhs_mod
        from src.pipeline.tasks.maintenance_tasks import reset_domain_health

        with patch.object(dhs_mod, "DomainHealthService", return_value=mock_service):
            result = reset_domain_health()

        assert result["domains_reset"] == 3
        mock_service.reset_stale_blocks.assert_called_once_with(older_than_days=7)


# ------------------------------------------------------------------
# cleanup_old_jobs
# ------------------------------------------------------------------


class TestCleanupOldJobs:
    """Tests for the cleanup_old_jobs task."""

    def test_cleanup_old_jobs_removes_terminal_only(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 12

        from src.pipeline.tasks.maintenance_tasks import cleanup_old_jobs

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            result = cleanup_old_jobs(days=90)

        assert result["deleted"] == 12
        assert result["cutoff_days"] == 90
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_cleanup_old_jobs_respects_cutoff(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        from src.pipeline.tasks.maintenance_tasks import cleanup_old_jobs

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            result = cleanup_old_jobs(days=30)

        assert result["deleted"] == 0
        assert result["cutoff_days"] == 30
        mock_db.commit.assert_called_once()

    def test_cleanup_old_jobs_handles_error(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.delete.side_effect = RuntimeError(
            "Table locked"
        )

        from src.pipeline.tasks.maintenance_tasks import cleanup_old_jobs

        with patch.object(db_mod, "SessionLocal", return_value=mock_db):
            result = cleanup_old_jobs()

        assert "error" in result
        assert "Table locked" in result["error"]
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
