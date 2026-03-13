from __future__ import annotations

import os
from typing import Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


REDIS_URL = os.getenv("REDIS_URL")
QUEUE_NAME = os.getenv("SANDBOX_QUEUE_NAME", "sandbox_queue")

_client = redis.from_url(REDIS_URL) if redis and REDIS_URL else None


def enqueue_sandbox_run(run_id: int) -> None:
    """
    Enqueue a sandbox run ID for processing.

    Uses Redis list `sandbox_queue` when available; otherwise this is a no-op
    and workers should fall back to polling the database for queued runs.
    """
    if _client is None:
        return
    _client.lpush(QUEUE_NAME, str(run_id))


def dequeue_sandbox_run(block: bool = True, timeout: int = 5) -> Optional[int]:
    """
    Dequeue a sandbox run ID from the queue.

    Returns None if the queue is empty or Redis is unavailable.
    """
    if _client is None:
        return None
    if block:
        item = _client.brpop(QUEUE_NAME, timeout=timeout)
    else:
        item = _client.rpop(QUEUE_NAME)
    if not item:
        return None
    # brpop returns (queue, value)
    value = item[1] if isinstance(item, (list, tuple)) else item
    try:
        return int(value)
    except Exception:
        return None

