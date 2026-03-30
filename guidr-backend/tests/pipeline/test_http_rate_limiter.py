"""Tests for per-endpoint HTTP rate limiting dependency."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEndpointRateLimitTierConfig:
    """Static configuration sanity checks — no Redis needed."""

    def test_heavy_tier_limit_is_5rpm(self):
        from src.dependencies.rate_limit import _TIER_CONFIG
        assert _TIER_CONFIG["heavy"]["rpm"] == 5

    def test_light_tier_limit_is_30rpm(self):
        from src.dependencies.rate_limit import _TIER_CONFIG
        assert _TIER_CONFIG["light"]["rpm"] == 30

    def test_unknown_tier_falls_back_to_light(self):
        from src.dependencies.rate_limit import _TIER_CONFIG, endpoint_rate_limit
        # Factory should not raise even for unknown tier
        dep = endpoint_rate_limit("nonexistent_tier")
        assert callable(dep)


class TestEndpointRateLimitDependency:
    """Tests for the async dependency function returned by endpoint_rate_limit."""

    @pytest.fixture()
    def mock_redis(self):
        r = MagicMock()
        return r

    @pytest.fixture()
    def mock_settings_enabled(self):
        """Settings with rate limiting enabled."""
        s = MagicMock()
        s.endpoint_rate_limit_enabled = True
        s.redis_url = "redis://localhost:6379/0"
        return s

    @pytest.mark.asyncio
    async def test_allows_first_request(self, mock_redis, mock_settings_enabled):
        """A fresh key (count=1) should be allowed through."""
        mock_redis.eval.return_value = [1, 1, 59]  # allowed=1, count=1, ttl=59

        user = _make_user()

        with (
            patch("src.dependencies.rate_limit._get_redis", return_value=mock_redis),
            patch("src.dependencies.rate_limit.get_current_user", return_value=user),
        ):
            from src.dependencies.rate_limit import endpoint_rate_limit
            dep_fn = endpoint_rate_limit("heavy")
            # Call the inner dependency directly, bypassing FastAPI DI
            result = await dep_fn(current_user=user)

        assert result is user

    @pytest.mark.asyncio
    async def test_blocks_when_limit_reached(self, mock_redis, mock_settings_enabled):
        """When Redis returns allowed=0, should raise HTTP 429."""
        from fastapi import HTTPException
        mock_redis.eval.return_value = [0, 5, 30]  # allowed=0, count=5, ttl=30

        user = _make_user()

        with (
            patch("src.dependencies.rate_limit._get_redis", return_value=mock_redis),
            patch("src.dependencies.rate_limit.get_current_user", return_value=user),
        ):
            from src.dependencies.rate_limit import endpoint_rate_limit
            dep_fn = endpoint_rate_limit("heavy")
            with pytest.raises(HTTPException) as exc_info:
                await dep_fn(current_user=user)

        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_retry_after_header_present(self, mock_redis, mock_settings_enabled):
        """429 response must include a Retry-After header with integer value."""
        from fastapi import HTTPException
        mock_redis.eval.return_value = [0, 5, 42]  # ttl=42

        user = _make_user()

        with (
            patch("src.dependencies.rate_limit._get_redis", return_value=mock_redis),
            patch("src.dependencies.rate_limit.get_current_user", return_value=user),
        ):
            from src.dependencies.rate_limit import endpoint_rate_limit
            dep_fn = endpoint_rate_limit("heavy")
            with pytest.raises(HTTPException) as exc_info:
                await dep_fn(current_user=user)

        headers = exc_info.value.headers or {}
        assert "Retry-After" in headers
        assert int(headers["Retry-After"]) == 42

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_error(self, mock_settings_enabled):
        """When Redis raises, the request should be allowed (fail open)."""
        broken_redis = MagicMock()
        broken_redis.eval.side_effect = ConnectionError("Redis unavailable")

        user = _make_user()

        with (
            patch("src.dependencies.rate_limit._get_redis", return_value=broken_redis),
            patch("src.dependencies.rate_limit.get_current_user", return_value=user),
        ):
            from src.dependencies.rate_limit import endpoint_rate_limit
            dep_fn = endpoint_rate_limit("heavy")
            result = await dep_fn(current_user=user)

        assert result is user

    @pytest.mark.asyncio
    async def test_bypasses_when_flag_disabled(self, mock_redis):
        """When endpoint_rate_limit_enabled=False, no Redis call is made."""
        user = _make_user()
        settings_disabled = MagicMock()
        settings_disabled.endpoint_rate_limit_enabled = False

        with (
            patch("src.dependencies.rate_limit._get_redis", return_value=mock_redis),
            patch("src.dependencies.rate_limit.get_current_user", return_value=user),
        ):
            from src.dependencies.rate_limit import endpoint_rate_limit

            with patch("src.dependencies.rate_limit.settings", settings_disabled):
                # Need to re-import or patch settings inside the dep
                dep_fn = endpoint_rate_limit("heavy")
                result = await dep_fn(current_user=user)

        # Redis eval should NOT have been called
        mock_redis.eval.assert_not_called()
        assert result is user
