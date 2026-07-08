"""Rate limiting middleware for FastAPI."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 120  # Increased for SPA navigation
    requests_per_hour: int = 3000
    burst_limit: int = 30  # Allow burst for page loads with multiple API calls

    # Different limits for different endpoint types
    auth_requests_per_minute: int = 20  # Auth endpoints
    ingestion_requests_per_minute: int = 10  # Admin endpoints


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)
    refill_rate: float = 1.0  # tokens per second

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class InMemoryRateLimiter:
    """In-memory rate limiter using token buckets."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: Dict[str, TokenBucket] = {}
        self._request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._window_start: Dict[str, float] = {}

    def _get_bucket(self, key: str, capacity: int, refill_rate: float) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        bucket_key = f"{key}:{capacity}"
        if bucket_key not in self._buckets:
            self._buckets[bucket_key] = TokenBucket(
                capacity=capacity,
                tokens=capacity,
                refill_rate=refill_rate
            )
        return self._buckets[bucket_key]

    def is_allowed(self, identifier: str, endpoint_type: str = "default") -> tuple[bool, dict]:
        """Check if request is allowed.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()

        # Get limits based on endpoint type
        if endpoint_type == "auth":
            rpm = self.config.auth_requests_per_minute
        elif endpoint_type == "ingestion":
            rpm = self.config.ingestion_requests_per_minute
        else:
            rpm = self.config.requests_per_minute

        # Token bucket for burst protection
        bucket = self._get_bucket(
            identifier,
            capacity=self.config.burst_limit,
            refill_rate=rpm / 60.0
        )

        # Check minute window
        minute_key = f"{identifier}:minute"
        window_start = self._window_start.get(minute_key, now)

        if now - window_start >= 60:
            # Reset window
            self._request_counts[minute_key] = defaultdict(int)
            self._window_start[minute_key] = now
            window_start = now

        current_count = self._request_counts[minute_key].get("count", 0)

        # Check limits
        if current_count >= rpm:
            retry_after = int(60 - (now - window_start))
            return False, {
                "limit": rpm,
                "remaining": 0,
                "reset": int(window_start + 60),
                "retry_after": max(1, retry_after)
            }

        if not bucket.consume():
            return False, {
                "limit": self.config.burst_limit,
                "remaining": 0,
                "reset": int(now + 1),
                "retry_after": 1
            }

        # Allow request
        self._request_counts[minute_key]["count"] = current_count + 1

        return True, {
            "limit": rpm,
            "remaining": rpm - current_count - 1,
            "reset": int(window_start + 60),
        }

    def cleanup_old_entries(self, max_age: float = 3600):
        """Remove old entries to prevent memory bloat."""
        now = time.time()
        old_keys = [
            k for k, v in self._window_start.items()
            if now - v > max_age
        ]
        for key in old_keys:
            self._window_start.pop(key, None)
            self._request_counts.pop(key, None)


class RedisRateLimiter:
    """Redis-based rate limiter for distributed deployments."""

    def __init__(self, config: RateLimitConfig, redis_url: str):
        self.config = config
        self._redis = redis.from_url(redis_url) if REDIS_AVAILABLE else None

    def is_allowed(self, identifier: str, endpoint_type: str = "default") -> tuple[bool, dict]:
        """Check if request is allowed using Redis."""
        if not self._redis:
            return True, {"limit": -1, "remaining": -1, "reset": 0}

        now = int(time.time())

        # Get limits based on endpoint type
        if endpoint_type == "auth":
            rpm = self.config.auth_requests_per_minute
        elif endpoint_type == "ingestion":
            rpm = self.config.ingestion_requests_per_minute
        else:
            rpm = self.config.requests_per_minute

        # Use sliding window with Redis
        key = f"ratelimit:{identifier}:{endpoint_type}"
        window_start = now - 60

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcount(key, window_start, now)
        pipe.expire(key, 120)
        _, _, count, _ = pipe.execute()

        if count > rpm:
            return False, {
                "limit": rpm,
                "remaining": 0,
                "reset": now + 60,
                "retry_after": 60
            }

        return True, {
            "limit": rpm,
            "remaining": rpm - count,
            "reset": now + 60,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/redoc"]

        if use_redis and redis_url and REDIS_AVAILABLE:
            self.limiter = RedisRateLimiter(self.config, redis_url)
        else:
            self.limiter = InMemoryRateLimiter(self.config)

    def _get_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP from headers (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type for rate limit rules."""
        if path.startswith("/auth/"):
            return "auth"
        if path.startswith("/ingestion/"):
            return "ingestion"
        return "default"

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""
        path = request.url.path

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)

        # Get identifier and check rate limit
        identifier = self._get_identifier(request)
        endpoint_type = self._get_endpoint_type(path)

        is_allowed, rate_info = self.limiter.is_allowed(identifier, endpoint_type)

        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after": rate_info.get("retry_after", 60)
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info.get("retry_after", 60))
                }
            )

        # Process request and add rate limit headers
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response


# Factory function for easy setup
def create_rate_limiter(
    use_redis: bool = False,
    redis_url: Optional[str] = None,
    requests_per_minute: int = 60,
    burst_limit: int = 10,
) -> RateLimitMiddleware:
    """Create a rate limiter middleware with custom configuration."""
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        burst_limit=burst_limit,
    )
    return lambda app: RateLimitMiddleware(
        app,
        config=config,
        use_redis=use_redis,
        redis_url=redis_url,
    )
