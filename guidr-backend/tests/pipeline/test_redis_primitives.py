"""Tests for Redis keyspace primitives: keys, fingerprint, dedup, quota, rate_limit."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


# ===================================================================== #
# 1. keys.py - pure functions, no mocking
# ===================================================================== #
class TestRedisKeys(unittest.TestCase):
    """Tests for src.pipeline.redis_keyspace.keys (pure functions)."""

    def test_dedup_lock_key(self):
        from src.pipeline.redis_keyspace.keys import dedup_lock_key
        assert dedup_lock_key("fp123") == "guidr:v1:dedup:lock:fp123"

    def test_quota_key(self):
        from src.pipeline.redis_keyspace.keys import quota_key
        assert quota_key("user1", "enrich", "day") == "guidr:v1:quota:user:user1:enrich:day"

    def test_circuit_breaker_key(self):
        from src.pipeline.redis_keyspace.keys import circuit_breaker_key
        assert circuit_breaker_key("host") == "guidr:v1:cb:domain:host"

    def test_enrichment_cache_key(self):
        from src.pipeline.redis_keyspace.keys import enrichment_cache_key
        result = enrichment_cache_key("school", "id1", "v1", "30d")
        assert result == "guidr:v1:cache:enrich:school:id1:v1:30d"

    def test_domain_error_streak_key(self):
        from src.pipeline.redis_keyspace.keys import domain_error_streak_key
        assert domain_error_streak_key("host") == "guidr:v1:cb:domain:host:streak"


# ===================================================================== #
# 2. fingerprint.py - pure functions
# ===================================================================== #
class TestFingerprint(unittest.TestCase):
    """Tests for src.pipeline.redis_keyspace.fingerprint."""

    def test_url_hash_valid_url(self):
        from src.pipeline.redis_keyspace.fingerprint import url_hash
        result = url_hash("https://MIT.edu")
        # SHA256 of lowercased URL
        import hashlib
        expected = hashlib.sha256("https://mit.edu".encode("utf-8")).hexdigest()
        assert result == expected

    def test_url_hash_none(self):
        from src.pipeline.redis_keyspace.fingerprint import url_hash
        assert url_hash(None) == "-"

    def test_url_hash_empty(self):
        from src.pipeline.redis_keyspace.fingerprint import url_hash
        assert url_hash("") == "-"

    def test_compute_job_fingerprint_returns_tuple(self):
        from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
        fp, fp_input = compute_job_fingerprint(
            job_type="research_discovery",
            entity_kind="school",
            entity_id="abc-123",
        )
        assert isinstance(fp, str)
        assert isinstance(fp_input, str)
        assert len(fp) == 64  # SHA256 hex length

    def test_compute_job_fingerprint_deterministic(self):
        from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
        kwargs = dict(
            job_type="scrape_fetch",
            schema_version="v1",
            freshness_bucket="7d",
            entity_kind="school",
            entity_id="uuid-1",
        )
        fp1, _ = compute_job_fingerprint(**kwargs)
        fp2, _ = compute_job_fingerprint(**kwargs)
        assert fp1 == fp2

    def test_compute_job_fingerprint_varies_with_freshness(self):
        from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
        fp1, _ = compute_job_fingerprint(
            job_type="scrape_fetch", freshness_bucket="7d", entity_id="x"
        )
        fp2, _ = compute_job_fingerprint(
            job_type="scrape_fetch", freshness_bucket="30d", entity_id="x"
        )
        assert fp1 != fp2

    def test_compute_job_fingerprint_varies_with_entity_id(self):
        from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
        fp1, _ = compute_job_fingerprint(job_type="scrape_fetch", entity_id="aaa")
        fp2, _ = compute_job_fingerprint(job_type="scrape_fetch", entity_id="bbb")
        assert fp1 != fp2


# ===================================================================== #
# 3. dedup.py - mock Redis
# ===================================================================== #
class TestDedup(unittest.TestCase):
    """Tests for src.pipeline.redis_keyspace.dedup."""

    @patch("src.pipeline.redis_keyspace.dedup._get_redis")
    def test_acquire_lock_success(self, mock_get_redis):
        from src.pipeline.redis_keyspace.dedup import acquire_lock

        mock_redis = MagicMock()
        mock_redis.eval.return_value = 1
        mock_get_redis.return_value = mock_redis

        result = acquire_lock("fp123", "job-1")
        assert result is True
        mock_redis.eval.assert_called_once()

    @patch("src.pipeline.redis_keyspace.dedup._get_redis")
    def test_acquire_lock_failure(self, mock_get_redis):
        from src.pipeline.redis_keyspace.dedup import acquire_lock

        mock_redis = MagicMock()
        mock_redis.eval.return_value = 0
        mock_get_redis.return_value = mock_redis

        result = acquire_lock("fp123", "job-1")
        assert result is False

    @patch("src.pipeline.redis_keyspace.dedup._get_redis")
    def test_release_lock_success(self, mock_get_redis):
        from src.pipeline.redis_keyspace.dedup import release_lock

        mock_redis = MagicMock()
        mock_redis.eval.return_value = 1
        mock_get_redis.return_value = mock_redis

        result = release_lock("fp123", "job-1")
        assert result is True

    @patch("src.pipeline.redis_keyspace.dedup._get_redis")
    def test_release_lock_not_owner(self, mock_get_redis):
        from src.pipeline.redis_keyspace.dedup import release_lock

        mock_redis = MagicMock()
        mock_redis.eval.return_value = 0
        mock_get_redis.return_value = mock_redis

        result = release_lock("fp123", "job-2")
        assert result is False


# ===================================================================== #
# 4. quota.py - mock Redis
# ===================================================================== #
class TestQuota(unittest.TestCase):
    """Tests for src.pipeline.redis_keyspace.quota."""

    @patch("src.pipeline.redis_keyspace.quota._get_redis")
    def test_check_and_increment_allowed(self, mock_get_redis):
        from src.pipeline.redis_keyspace.quota import check_and_increment_quota

        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 3]
        mock_get_redis.return_value = mock_redis

        result = check_and_increment_quota("user1", "enrich", "day", limit=50)
        assert result.allowed is True
        assert result.current == 3
        assert result.remaining == 47

    @patch("src.pipeline.redis_keyspace.quota._get_redis")
    def test_check_and_increment_denied(self, mock_get_redis):
        from src.pipeline.redis_keyspace.quota import check_and_increment_quota

        mock_redis = MagicMock()
        mock_redis.eval.return_value = [0, 50]
        mock_get_redis.return_value = mock_redis

        result = check_and_increment_quota("user1", "enrich", "day", limit=50)
        assert result.allowed is False
        assert result.current == 50
        assert result.remaining == 0

    @patch("src.pipeline.redis_keyspace.quota._get_redis")
    def test_check_and_increment_fail_open(self, mock_get_redis):
        from src.pipeline.redis_keyspace.quota import check_and_increment_quota

        mock_redis = MagicMock()
        mock_redis.eval.side_effect = Exception("Redis down")
        mock_get_redis.return_value = mock_redis

        result = check_and_increment_quota("user1", "enrich", "day", limit=50)
        assert result.allowed is True  # fail-open


# ===================================================================== #
# 5. rate_limit.py - mock Redis
# ===================================================================== #
class TestRateLimit(unittest.TestCase):
    """Tests for src.pipeline.redis_keyspace.rate_limit."""

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_take_token_allowed(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import take_token

        mock_redis = MagicMock()
        mock_redis.eval.return_value = [1, 2.5]
        mock_get_redis.return_value = mock_redis

        result = take_token("mit.edu")
        assert result.allowed is True
        assert result.tokens_left == 2.5

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_take_token_denied(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import take_token

        mock_redis = MagicMock()
        mock_redis.eval.return_value = [0, 0.0]
        mock_get_redis.return_value = mock_redis

        result = take_token("mit.edu")
        assert result.allowed is False
        assert result.tokens_left == 0.0

    def test_host_from_url_https(self):
        from src.pipeline.redis_keyspace.rate_limit import _host_from_url
        assert _host_from_url("https://mit.edu/page") == "mit.edu"

    def test_host_from_url_bare(self):
        from src.pipeline.redis_keyspace.rate_limit import _host_from_url
        assert _host_from_url("mit.edu") == "mit.edu"

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_check_circuit_breaker_open(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import check_circuit_breaker

        mock_redis = MagicMock()
        mock_redis.get.return_value = b"1"
        mock_get_redis.return_value = mock_redis

        assert check_circuit_breaker("bad-host.com") is True

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_check_circuit_breaker_closed(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import check_circuit_breaker

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        assert check_circuit_breaker("good-host.com") is False

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_record_domain_error_increments_and_trips_cb(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import record_domain_error

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [5, True]  # streak=5
        mock_redis.pipeline.return_value = mock_pipe
        mock_get_redis.return_value = mock_redis

        streak = record_domain_error("bad.com", threshold=5)
        assert streak == 5
        mock_redis.setex.assert_called_once()

    @patch("src.pipeline.redis_keyspace.rate_limit._get_redis")
    def test_record_domain_success_deletes_streak(self, mock_get_redis):
        from src.pipeline.redis_keyspace.rate_limit import record_domain_success

        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        record_domain_success("good.com")
        mock_redis.delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
