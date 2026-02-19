"""Dedup lock: acquire and release for job fingerprint."""
from __future__ import annotations

import logging
from typing import Optional

from src.pipeline.redis_keyspace.keys import dedup_lock_key
from src.pipeline.redis_keyspace.lua_scripts import ACQUIRE_LOCK, RELEASE_LOCK

logger = logging.getLogger(__name__)

DEFAULT_LOCK_TTL_MS = 600_000  # 10 minutes


def _get_redis():
    """Lazy import to avoid circular deps."""
    import redis
    from src.config import settings
    return redis.from_url(settings.redis_url)


def acquire_lock(fingerprint: str, job_id: str, ttl_ms: int = DEFAULT_LOCK_TTL_MS) -> bool:
    """Acquire dedup lock for fingerprint. Returns True if acquired."""
    r = _get_redis()
    key = dedup_lock_key(fingerprint)
    try:
        result = r.eval(ACQUIRE_LOCK, 1, key, job_id, str(ttl_ms))
        return bool(result and result != 0)
    except Exception as exc:
        logger.warning("acquire_lock failed: %s", exc)
        return False


def release_lock(fingerprint: str, job_id: str) -> bool:
    """Release dedup lock only if owned by job_id. Returns True if released."""
    r = _get_redis()
    key = dedup_lock_key(fingerprint)
    try:
        result = r.eval(RELEASE_LOCK, 1, key, job_id)
        return bool(result and result != 0)
    except Exception as exc:
        logger.warning("release_lock failed: %s", exc)
        return False
