"""Redis keyspace for pipeline: dedup, rate limiting, quotas, cache pointers."""
from src.pipeline.redis_keyspace.fingerprint import compute_job_fingerprint
from src.pipeline.redis_keyspace.dedup import acquire_lock, release_lock
from src.pipeline.redis_keyspace.rate_limit import (
    take_token,
    take_token_for_url,
    quota_increment,
    TokenResult,
    check_circuit_breaker,
    record_domain_error,
    record_domain_success,
)
from src.pipeline.redis_keyspace.quota import (
    check_and_increment_quota,
    get_quota_usage,
    QuotaResult,
)
from src.pipeline.redis_keyspace.keys import (
    dedup_lock_key,
    rate_limit_domain_tokens_key,
    quota_key,
    circuit_breaker_key,
    domain_error_streak_key,
)

__all__ = [
    "compute_job_fingerprint",
    "acquire_lock",
    "release_lock",
    "take_token",
    "take_token_for_url",
    "quota_increment",
    "TokenResult",
    "check_circuit_breaker",
    "record_domain_error",
    "record_domain_success",
    "check_and_increment_quota",
    "get_quota_usage",
    "QuotaResult",
    "dedup_lock_key",
    "rate_limit_domain_tokens_key",
    "quota_key",
    "circuit_breaker_key",
    "domain_error_streak_key",
]
