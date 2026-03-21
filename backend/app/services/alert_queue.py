from __future__ import annotations

import os
from typing import Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


REDIS_URL = os.getenv("REDIS_URL")
QUEUE_NAME = os.getenv("ALERT_QUEUE_NAME", "security_alert_dispatch_queue")

_client = redis.from_url(REDIS_URL) if redis and REDIS_URL else None


def enqueue_alert_dispatch(alert_id: int) -> None:
    """
    Enqueue a security alert ID for dispatching to notification channels.
    """
    if _client is None:
        return
    _client.lpush(QUEUE_NAME, str(alert_id))


def dequeue_alert_dispatch(block: bool = True, timeout: int = 5) -> Optional[int]:
    """
    Dequeue a security alert ID from the dispatch queue.
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
