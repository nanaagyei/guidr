"""Lua scripts for atomic Redis operations."""
from __future__ import annotations

TAKE_TOKEN = """
local tokens_key = KEYS[1]
local ts_key     = KEYS[2]

local now_ms     = tonumber(ARGV[1])
local rate       = tonumber(ARGV[2])
local burst      = tonumber(ARGV[3])
local cost       = tonumber(ARGV[4])

local tokens = tonumber(redis.call("GET", tokens_key))
if tokens == nil then tokens = burst end

local ts = tonumber(redis.call("GET", ts_key))
if ts == nil then ts = now_ms end

local delta = math.max(0, now_ms - ts)
local refill = delta * rate
tokens = math.min(burst, tokens + refill)

local allowed = 0
if tokens >= cost then
  tokens = tokens - cost
  allowed = 1
end

redis.call("SET", tokens_key, tokens)
redis.call("SET", ts_key, now_ms)

redis.call("PEXPIRE", tokens_key, 3600000)
redis.call("PEXPIRE", ts_key, 3600000)

return {allowed, tokens}
"""

ACQUIRE_LOCK = """
local lock_key = KEYS[1]
local job_id   = ARGV[1]
local ttl_ms   = tonumber(ARGV[2])

local ok = redis.call("SET", lock_key, job_id, "NX", "PX", ttl_ms)
if ok then return 1 else return 0 end
"""

RELEASE_LOCK = """
local lock_key = KEYS[1]
local job_id   = ARGV[1]

local current = redis.call("GET", lock_key)
if current == job_id then
  redis.call("DEL", lock_key)
  return 1
end
return 0
"""

CHECK_QUOTA = """
local key       = KEYS[1]
local limit     = tonumber(ARGV[1])
local ttl_secs  = tonumber(ARGV[2])

local current = tonumber(redis.call("GET", key))
if current == nil then current = 0 end

if current >= limit then
  return {0, current}
end

current = redis.call("INCR", key)
if current == 1 then
  redis.call("EXPIRE", key, ttl_secs)
end

return {1, current}
"""
