"""Token bucket rate limiter (per-domain) + circuit breaker."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from src.pipeline.redis_keyspace.keys import (
    circuit_breaker_key,
    domain_error_streak_key,
    rate_limit_domain_tokens_key,
    rate_limit_domain_ts_key,
)
from src.pipeline.redis_keyspace.lua_scripts import TAKE_TOKEN

logger = logging.getLogger(__name__)

# Default: 10 req/min = 0.167 tokens/sec; burst 3
DEFAULT_REFILL_RATE_PER_SEC = 10 / 60
DEFAULT_BURST = 3
DEFAULT_COST = 1


@dataclass
class TokenResult:
    allowed: bool
    tokens_left: float


def _get_redis():
    import redis
    from src.config import settings
    return redis.from_url(settings.redis_url)


def _host_from_url(url: str) -> str:
    """Extract host from URL for rate limit key."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc or parsed.path.split("/")[0] or "unknown"
    except Exception:
        return "unknown"


def take_token(
    host: str,
    refill_rate_per_sec: float = DEFAULT_REFILL_RATE_PER_SEC,
    burst: int = DEFAULT_BURST,
    cost: int = DEFAULT_COST,
) -> TokenResult:
    """Atomically take tokens from bucket. Returns allowed, tokens_left."""
    r = _get_redis()
    tokens_key = rate_limit_domain_tokens_key(host)
    ts_key = rate_limit_domain_ts_key(host)
    now_ms = int(time.time() * 1000)
    rate_per_ms = refill_rate_per_sec / 1000.0
    try:
        result = r.eval(TAKE_TOKEN, 2, tokens_key, ts_key, now_ms, rate_per_ms, burst, cost)
        if result and len(result) >= 2:
            allowed = int(result[0]) == 1
            tokens_left = float(result[1])
            return TokenResult(allowed=allowed, tokens_left=tokens_left)
    except Exception as exc:
        logger.warning("take_token failed for %s: %s", host, exc)
    return TokenResult(allowed=False, tokens_left=0.0)


def take_token_for_url(
    url: str,
    refill_rate_per_sec: float = DEFAULT_REFILL_RATE_PER_SEC,
    burst: int = DEFAULT_BURST,
    cost: int = DEFAULT_COST,
) -> TokenResult:
    """Take token using host extracted from URL."""
    host = _host_from_url(url)
    return take_token(host, refill_rate_per_sec, burst, cost)


def quota_increment(key: str, ttl_seconds: int = 3600) -> int:
    """Increment quota counter. Sets TTL on first use. Returns new value."""
    r = _get_redis()
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        results = pipe.execute()
        return int(results[0]) if results else 0
    except Exception as exc:
        logger.warning("quota_increment failed for %s: %s", key, exc)
        return 0


# --- Circuit breaker ---

CIRCUIT_BREAKER_THRESHOLD = 5  # consecutive errors to trip
CIRCUIT_BREAKER_COOLDOWN = 600  # seconds (10 minutes)


def check_circuit_breaker(host: str) -> bool:
    """Check if the circuit breaker is open (True = blocked)."""
    r = _get_redis()
    try:
        val = r.get(circuit_breaker_key(host))
        return val is not None
    except Exception as exc:
        logger.warning("check_circuit_breaker failed for %s: %s", host, exc)
        return False


def record_domain_error(
    host: str,
    threshold: int = CIRCUIT_BREAKER_THRESHOLD,
    cooldown_seconds: int = CIRCUIT_BREAKER_COOLDOWN,
) -> int:
    """Record a domain error. Trips circuit breaker if threshold exceeded.

    Returns the current error streak count.
    """
    r = _get_redis()
    streak_key = domain_error_streak_key(host)
    cb_key = circuit_breaker_key(host)
    try:
        pipe = r.pipeline()
        pipe.incr(streak_key)
        pipe.expire(streak_key, cooldown_seconds * 2)
        results = pipe.execute()
        streak = int(results[0]) if results else 1

        if streak >= threshold:
            r.setex(cb_key, cooldown_seconds, "1")
            logger.warning("Circuit breaker tripped for %s (streak=%d)", host, streak)

        return streak
    except Exception as exc:
        logger.warning("record_domain_error failed for %s: %s", host, exc)
        return 0


def record_domain_success(host: str) -> None:
    """Record a domain success, resetting the error streak."""
    r = _get_redis()
    streak_key = domain_error_streak_key(host)
    try:
        r.delete(streak_key)
    except Exception as exc:
        logger.warning("record_domain_success failed for %s: %s", host, exc)
