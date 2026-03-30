"""Per-endpoint, per-user HTTP rate limiting FastAPI dependency.

Usage:
    from src.dependencies.rate_limit import endpoint_rate_limit

    @router.post("/heavy-endpoint")
    async def my_endpoint(
        current_user: User = Depends(endpoint_rate_limit("heavy")),
        db: Session = Depends(get_db),
    ):
        ...

The dependency returns the authenticated User object so the route handler
does not need a separate ``Depends(get_current_user)``.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Depends, HTTPException, status

from src.dependencies.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

# Tier configuration: requests per minute and burst size.
_TIER_CONFIG: dict[str, dict] = {
    # Heavy endpoints: dossier research, professor matching, funding research,
    # recommendations/run.  These invoke LLM pipelines.
    "heavy": {"rpm": 5, "burst": 5},
    # Light endpoints: job status polling, cache reads, enrichment status.
    "light": {"rpm": 30, "burst": 30},
}

# Simple sliding-window counter: INCR + EXPIRE.
# Returns {allowed, count, ttl_remaining}.
_ENDPOINT_RL_SCRIPT = """
local key    = KEYS[1]
local limit  = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local count = tonumber(redis.call("GET", key))
if count == nil then count = 0 end

if count >= limit then
  local ttl = redis.call("TTL", key)
  return {0, count, ttl > 0 and ttl or window}
end

count = redis.call("INCR", key)
if count == 1 then
  redis.call("EXPIRE", key, window)
end
local ttl = redis.call("TTL", key)
return {1, count, ttl > 0 and ttl or window}
"""


def _get_redis():
    import redis as redis_lib
    from src.config import settings
    return redis_lib.from_url(settings.redis_url, decode_responses=False)


def endpoint_rate_limit(tier: str) -> Callable:
    """Factory: return a FastAPI dependency that enforces *tier* rate limits.

    The dependency also authenticates the caller and returns the User, so
    routes can replace ``Depends(get_current_user)`` with
    ``Depends(endpoint_rate_limit("heavy"))``.

    When Redis is unavailable the dependency fails open (allows the request).
    When the feature flag ``endpoint_rate_limit_enabled`` is False, the
    dependency also fails open (useful for emergency bypasses).
    """
    config = _TIER_CONFIG.get(tier, _TIER_CONFIG["light"])
    rpm: int = config["rpm"]
    window: int = 60  # seconds

    async def _rate_limit_dep(
        current_user: User = Depends(get_current_user),
    ) -> User:
        from src.config import settings

        if not settings.endpoint_rate_limit_enabled:
            return current_user

        user_id = str(current_user.id)
        key = f"guidr:v1:rl:endpoint:{user_id}:{tier}"

        try:
            r = _get_redis()
            result = r.eval(_ENDPOINT_RL_SCRIPT, 1, key, rpm, window)
            allowed = int(result[0]) == 1
            ttl = int(result[2]) if result[2] else window

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded for {tier} endpoints. "
                        f"Limit: {rpm} requests/minute."
                    ),
                    headers={"Retry-After": str(ttl)},
                )
        except HTTPException:
            raise
        except Exception as exc:
            # Fail open — log and allow when Redis is unavailable
            logger.warning(
                "endpoint_rate_limit Redis error for user=%s tier=%s: %s",
                user_id, tier, exc,
            )

        return current_user

    return _rate_limit_dep
