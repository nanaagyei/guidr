"""Redis-based user quota enforcement with atomic Lua check-and-increment."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.pipeline.redis_keyspace.keys import quota_key
from src.pipeline.redis_keyspace.lua_scripts import CHECK_QUOTA

logger = logging.getLogger(__name__)

# Default quota limits
DEFAULT_ENRICHMENT_LIMIT_PER_DAY = 50
DEFAULT_RESEARCH_LIMIT_PER_DAY = 10


@dataclass
class QuotaResult:
    allowed: bool
    current: int
    limit: int
    remaining: int


def _get_redis():
    import redis
    from src.config import settings
    return redis.from_url(settings.redis_url)


def check_and_increment_quota(
    user_id: str,
    resource: str = "enrich",
    period: str = "day",
    limit: int = DEFAULT_ENRICHMENT_LIMIT_PER_DAY,
) -> QuotaResult:
    """Atomically check quota and increment if allowed.

    Uses a Lua script to prevent race conditions between check and increment.

    Args:
        user_id: The user requesting the action.
        resource: 'enrich' or 'research'.
        period: 'hour' or 'day'.
        limit: Maximum allowed actions in the period.

    Returns:
        QuotaResult with allowed flag and usage info.
    """
    r = _get_redis()
    key = quota_key(user_id, resource, period)
    ttl_seconds = 86400 if period == "day" else 3600

    try:
        result = r.eval(CHECK_QUOTA, 1, key, limit, ttl_seconds)
        if result and len(result) >= 2:
            allowed = int(result[0]) == 1
            current = int(result[1])
            return QuotaResult(
                allowed=allowed,
                current=current,
                limit=limit,
                remaining=max(0, limit - current),
            )
    except Exception as exc:
        logger.warning("check_and_increment_quota failed for user %s: %s", user_id, exc)

    # Fail open: allow the request if Redis is unavailable
    return QuotaResult(allowed=True, current=0, limit=limit, remaining=limit)


def get_quota_usage(user_id: str, resource: str = "enrich", period: str = "day") -> int:
    """Read current quota usage without incrementing."""
    r = _get_redis()
    key = quota_key(user_id, resource, period)
    try:
        val = r.get(key)
        return int(val) if val else 0
    except Exception as exc:
        logger.warning("get_quota_usage failed for user %s: %s", user_id, exc)
        return 0
