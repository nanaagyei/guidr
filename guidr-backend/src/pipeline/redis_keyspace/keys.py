"""Redis key builders for pipeline (guidr:v1: prefix)."""
from __future__ import annotations

PREFIX = "guidr:v1"


def dedup_lock_key(fingerprint: str) -> str:
    return f"{PREFIX}:dedup:lock:{fingerprint}"


def dedup_result_key(fingerprint: str) -> str:
    return f"{PREFIX}:dedup:result:{fingerprint}"


def rate_limit_domain_tokens_key(host: str) -> str:
    return f"{PREFIX}:rl:domain:{host}:tokens"


def rate_limit_domain_ts_key(host: str) -> str:
    return f"{PREFIX}:rl:domain:{host}:ts"


def inflight_key(service: str) -> str:
    """service: fetch, research, extract."""
    return f"{PREFIX}:rl:global:{service}:inflight"


def enrichment_cache_key(entity_kind: str, entity_id: str, schema_version: str, freshness_bucket: str) -> str:
    return f"{PREFIX}:cache:enrich:{entity_kind}:{entity_id}:{schema_version}:{freshness_bucket}"


def quota_key(user_id: str, resource: str, period: str) -> str:
    """resource: enrich, research; period: hour, day."""
    return f"{PREFIX}:quota:user:{user_id}:{resource}:{period}"


def circuit_breaker_key(host: str) -> str:
    """Circuit breaker flag for a domain."""
    return f"{PREFIX}:cb:domain:{host}"


def domain_error_streak_key(host: str) -> str:
    """Error streak counter for a domain."""
    return f"{PREFIX}:cb:domain:{host}:streak"
