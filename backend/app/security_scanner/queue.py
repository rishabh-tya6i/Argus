from __future__ import annotations

import os
from typing import Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


REDIS_URL = os.getenv("REDIS_URL")
QUEUE_NAME = os.getenv("SECURITY_SCAN_QUEUE_NAME", "security_scan_queue")

_client = redis.from_url(REDIS_URL) if redis and REDIS_URL else None


def enqueue_security_scan(run_id: int) -> None:
    """
    Enqueue a security scan run ID for processing.
    """
    if _client is None:
        return
    _client.lpush(QUEUE_NAME, str(run_id))


def dequeue_security_scan(block: bool = True, timeout: int = 5) -> Optional[int]:
    """
    Dequeue a security scan run ID from the queue.
    """
    if _client is None:
        return None
    if block:
        item = _client.brpop(QUEUE_NAME, timeout=timeout)
    else:
        item = _client.rpop(QUEUE_NAME)
    if not item:
        return None
    value = item[1] if isinstance(item, (list, tuple)) else item
    try:
        return int(value)
    except Exception:
        return None
