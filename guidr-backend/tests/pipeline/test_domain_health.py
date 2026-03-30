"""Tests for DomainHealthService: record_success, record_error, is_blocked, admin queries."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call


class TestDomainHealthService(unittest.TestCase):
    """Tests for src.pipeline.services.domain_health_service.DomainHealthService."""

    def _get_mod(self):
        from src.pipeline.services import domain_health_service as mod
        return mod

    def _make_service(self):
        mod = self._get_mod()
        return mod.DomainHealthService()

    def _mock_db_with_row(self, row=None):
        """Return a mock SessionLocal that yields a mock db whose query chain returns row."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = row
        return mock_db

    # ------------------------------------------------------------------ #
    # 1. record_success clears streak and creates row
    # ------------------------------------------------------------------ #
    def test_record_success_clears_streak_creates_row(self):
        mod = self._get_mod()
        mock_db = self._mock_db_with_row(None)  # no existing row

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "redis_record_success") as mock_redis_success:
            svc = self._make_service()
            svc.record_success("example.com")

            mock_redis_success.assert_called_once_with("example.com")
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

            added_row = mock_db.add.call_args[0][0]
            assert added_row.host == "example.com"
            assert added_row.error_streak == 0

    # ------------------------------------------------------------------ #
    # 2. record_success resets existing blocked row
    # ------------------------------------------------------------------ #
    def test_record_success_resets_existing_block(self):
        mod = self._get_mod()
        existing = MagicMock()
        existing.block_detected = True
        existing.error_streak = 8
        mock_db = self._mock_db_with_row(existing)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "redis_record_success") as mock_redis_success:
            svc = self._make_service()
            svc.record_success("example.com")

            assert existing.error_streak == 0
            assert existing.block_detected is False
            assert existing.next_allowed_at is None
            mock_db.commit.assert_called_once()

    # ------------------------------------------------------------------ #
    # 3. record_error increments streak
    # ------------------------------------------------------------------ #
    def test_record_error_increments_streak(self):
        mod = self._get_mod()
        existing = MagicMock()
        existing.error_streak = 3
        mock_db = self._mock_db_with_row(existing)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "redis_record_error") as mock_redis_error:
            svc = self._make_service()
            result = svc.record_error("example.com", http_status=500)

            assert existing.error_streak == 4
            assert result == 4
            mock_redis_error.assert_called_once_with("example.com")

    # ------------------------------------------------------------------ #
    # 4. record_error blocks at threshold
    # ------------------------------------------------------------------ #
    def test_record_error_blocks_at_threshold(self):
        mod = self._get_mod()
        existing = MagicMock()
        existing.error_streak = 9  # will become 10 == threshold
        mock_db = self._mock_db_with_row(existing)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "redis_record_error") as mock_redis_error:
            svc = self._make_service()
            result = svc.record_error("bad.com")

            assert existing.error_streak == 10
            assert existing.block_detected is True
            assert existing.next_allowed_at is not None
            mock_db.commit.assert_called_once()

    # ------------------------------------------------------------------ #
    # 5. is_blocked - Redis says True
    # ------------------------------------------------------------------ #
    def test_is_blocked_redis_true(self):
        mod = self._get_mod()

        with patch.object(mod, "SessionLocal") as mock_session_cls, \
             patch.object(mod, "check_circuit_breaker", return_value=True):
            svc = self._make_service()
            assert svc.is_blocked("bad.com") is True
            # Should not hit Postgres at all
            mock_session_cls.assert_not_called()

    # ------------------------------------------------------------------ #
    # 6. is_blocked - Redis false, Postgres blocked
    # ------------------------------------------------------------------ #
    def test_is_blocked_redis_false_postgres_blocked(self):
        mod = self._get_mod()
        row = MagicMock()
        row.block_detected = True
        row.next_allowed_at = datetime.utcnow() + timedelta(hours=12)
        mock_db = self._mock_db_with_row(row)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "check_circuit_breaker", return_value=False):
            svc = self._make_service()
            assert svc.is_blocked("bad.com") is True

    # ------------------------------------------------------------------ #
    # 7. is_blocked - no row in Postgres
    # ------------------------------------------------------------------ #
    def test_is_blocked_false_no_row(self):
        mod = self._get_mod()
        mock_db = self._mock_db_with_row(None)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "check_circuit_breaker", return_value=False):
            svc = self._make_service()
            assert svc.is_blocked("good.com") is False

    # ------------------------------------------------------------------ #
    # 8. is_blocked - false after cooldown expired
    # ------------------------------------------------------------------ #
    def test_is_blocked_false_after_cooldown(self):
        mod = self._get_mod()
        row = MagicMock()
        row.block_detected = True
        row.next_allowed_at = datetime.utcnow() - timedelta(hours=1)  # expired
        mock_db = self._mock_db_with_row(row)

        with patch.object(mod, "SessionLocal", return_value=mock_db), \
             patch.object(mod, "check_circuit_breaker", return_value=False):
            svc = self._make_service()
            assert svc.is_blocked("recovering.com") is False

    # ------------------------------------------------------------------ #
    # 9. get_all_health returns list of dicts
    # ------------------------------------------------------------------ #
    def test_get_all_health_returns_list(self):
        mod = self._get_mod()
        row = MagicMock()
        row.host = "example.com"
        row.last_ok_at = datetime(2025, 1, 1)
        row.last_error_at = None
        row.error_streak = 0
        row.block_detected = False
        row.next_allowed_at = None
        row.notes = None

        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [row]

        with patch.object(mod, "SessionLocal", return_value=mock_db):
            svc = self._make_service()
            result = svc.get_all_health()

            assert len(result) == 1
            assert result[0]["host"] == "example.com"
            assert result[0]["error_streak"] == 0

    # ------------------------------------------------------------------ #
    # 10. reset_stale_blocks resets old entries
    # ------------------------------------------------------------------ #
    def test_reset_stale_blocks_resets_old_entries(self):
        mod = self._get_mod()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.update.return_value = 3

        with patch.object(mod, "SessionLocal", return_value=mock_db):
            svc = self._make_service()
            count = svc.reset_stale_blocks(older_than_days=7)

            assert count == 3
            mock_db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
