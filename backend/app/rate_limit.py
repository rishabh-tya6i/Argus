import os
import time
from typing import Dict, Optional

from fastapi import Request, HTTPException

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    redis = None


class InMemoryRateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.store: Dict[str, Dict[str, float | int]] = {}

    def check(self, key: str):
        now = time.time()
        entry = self.store.get(key)
        if entry is None or now - entry["start"] >= self.window:
            self.store[key] = {"start": now, "count": 1}
            return
        entry["count"] = int(entry["count"]) + 1
        if entry["count"] > self.limit:
            raise HTTPException(status_code=429, detail="rate_limited")


limiter = InMemoryRateLimiter()


REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL) if redis and REDIS_URL else None


def _check_with_redis(key: str, limit: int, window_seconds: int):
    assert redis_client is not None
    now = int(time.time())
    pipeline = redis_client.pipeline()
    pipeline.incr(key)
    pipeline.expire(key, window_seconds)
    count, _ = pipeline.execute()
    if int(count) > limit:
        raise HTTPException(status_code=429, detail="rate_limited")


async def rate_limit_dependency(request: Request):
    """
    Tenant-aware rate limiting with Redis, falling back to an in-memory limiter.

    - When tenant_id is available on the request (via JWT or API key), we use it
      as the primary key to prevent noisy neighbors between tenants.
    - Otherwise we fall back to client IP-based limiting.
    """
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    tenant_id = getattr(request.state, "tenant_id", None)
    key = f"rl:{tenant_id or ip}:{path}"

    # Default limits; can later be made tenant-configurable
    limit = 60
    window_seconds = 60

    if redis_client is not None:
        try:
            _check_with_redis(key, limit=limit, window_seconds=window_seconds)
            return
        except HTTPException:
            raise
        except Exception:
            # If Redis is unavailable, fall back to local limiter
            pass

    limiter.check(key)
