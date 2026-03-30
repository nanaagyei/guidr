"""Global inflight semaphore for pipeline job concurrency control.

Uses atomic Redis INCR/DECR Lua scripts to enforce a configurable cap on
concurrent dossier/professor-match jobs.  Fails open if Redis is unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default cap (overridable via settings.max_concurrent_dossier_jobs)
DEFAULT_MAX_CONCURRENT = 10

# TTL longer than the hard Celery time-limit (600 s) so stale counters
# eventually self-heal even if a worker is killed without calling release.
INFLIGHT_TTL_MS = 900_000  # 15 minutes


@dataclass
class InflightResult:
    """Result of an acquire_inflight() call."""
    acquired: bool
    current: int
    maximum: int


def _get_redis():
    import redis as redis_lib
    from src.config import settings
    return redis_lib.from_url(settings.redis_url, decode_responses=False)


def acquire_inflight(
    service: str = "dossier",
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> InflightResult:
    """Atomically check and increment the inflight counter for *service*.

    Returns:
        InflightResult with ``acquired=True`` when under cap.
        Fails open (``acquired=True``) when Redis is unavailable.
    """
    from src.pipeline.redis_keyspace.keys import inflight_key
    from src.pipeline.redis_keyspace.lua_scripts import INFLIGHT_INCR

    key = inflight_key(service)
    try:
        r = _get_redis()
        result = r.eval(INFLIGHT_INCR, 1, key, max_concurrent, INFLIGHT_TTL_MS)
        if result and len(result) >= 2:
            acquired = int(result[0]) == 1
            current = int(result[1])
            return InflightResult(acquired=acquired, current=current, maximum=max_concurrent)
    except Exception as exc:
        logger.warning("acquire_inflight Redis error for service=%s: %s", service, exc)

    # Fail open — do not block requests when Redis is down
    return InflightResult(acquired=True, current=0, maximum=max_concurrent)


def release_inflight(service: str = "dossier") -> int:
    """Decrement the inflight counter for *service*.

    Should be called in a ``finally`` block to ensure the slot is always
    released, even on task failure.

    Returns:
        New counter value (0 if Redis is unavailable or key was missing).
    """
    from src.pipeline.redis_keyspace.keys import inflight_key
    from src.pipeline.redis_keyspace.lua_scripts import INFLIGHT_DECR

    key = inflight_key(service)
    try:
        r = _get_redis()
        result = r.eval(INFLIGHT_DECR, 1, key)
        return int(result) if result is not None else 0
    except Exception as exc:
        logger.warning("release_inflight Redis error for service=%s: %s", service, exc)
        return 0
