"""
Security Alert Dispatch worker.

This worker consumes alert IDs from the security_alert_dispatch_queue (via Redis)
and executes the notification dispatch logic for each alert.
"""

from __future__ import annotations

import asyncio
import time
import traceback
import logging

from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..services.alert_queue import dequeue_alert_dispatch
from ..services.notification_service import dispatch_security_alert_notifications
from ..observability import (
    update_worker_heartbeat,
    setup_logging,
    QUEUE_DEPTH,
    QUEUE_PROCESSING_SECONDS,
    QUEUE_JOBS_TOTAL,
    WORKER_FAILURES_TOTAL,
    set_correlation_ctx,
    get_correlation_ctx,
)

logger = logging.getLogger(__name__)

_WORKER = "alert_dispatch"


async def process_single_alert(alert_id: int, db: Session) -> None:
    set_correlation_ctx(
        alert_id=str(alert_id),
        worker_name=_WORKER,
    )

    processing_start = time.perf_counter()
    try:
        await dispatch_security_alert_notifications(db, alert_id)
        QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="success").inc()
        logger.info(
            "Alert notification dispatch completed",
            extra={**get_correlation_ctx(), "event": "alert_dispatch_completed"},
        )
    except Exception as exc:
        QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="failed").inc()
        WORKER_FAILURES_TOTAL.labels(worker=_WORKER).inc()
        logger.error(
            "Alert notification dispatch failed",
            extra={
                **get_correlation_ctx(),
                "event": "alert_dispatch_error",
                "worker_name": _WORKER,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise
    finally:
        elapsed = time.perf_counter() - processing_start
        QUEUE_PROCESSING_SECONDS.labels(worker=_WORKER).observe(elapsed)


async def worker_loop() -> None:  # pragma: no cover
    setup_logging()
    init_db()
    logger.info(f"Starting {_WORKER} worker loop")
    set_correlation_ctx(worker_name=_WORKER)
    db = SessionLocal()
    try:
        while True:
            update_worker_heartbeat(_WORKER)

            # Prefer Redis queue if available
            alert_id = dequeue_alert_dispatch(block=True, timeout=5)
            if alert_id is not None:
                QUEUE_DEPTH.labels(worker=_WORKER).dec()
                await process_single_alert(alert_id, db)
                continue

            # Nothing to do, sleep briefly
            await asyncio.sleep(2)
    finally:
        db.close()


def main() -> None:  # pragma: no cover
    asyncio.run(worker_loop())


if __name__ == "__main__":  # pragma: no cover
    main()
