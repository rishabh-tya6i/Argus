"""
Sandbox worker.

This worker consumes sandbox run jobs (via Redis queue when available or by
polling the database) and executes them using the sandbox runner.
"""

from __future__ import annotations

import asyncio
import time
import traceback
import logging

from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..sandbox.queue import dequeue_sandbox_run
from ..sandbox.runner import execute_sandbox_run
from ..services.alert_service import create_security_alert
from ..db_models import SandboxRun, SandboxStatus, SecurityAlertType, AlertSeverity
from ..observability import (
    tracer,
    set_correlation_ctx,
    get_correlation_ctx,
    update_worker_heartbeat,
    setup_logging,
    SANDBOX_RUNS_TOTAL,
    WORKER_FAILURES_TOTAL,
    QUEUE_DEPTH,
    QUEUE_WAIT_SECONDS,
    QUEUE_PROCESSING_SECONDS,
    QUEUE_JOBS_TOTAL,
)

logger = logging.getLogger(__name__)

_WORKER = "sandbox"


def _get_next_queued_run(db: Session) -> SandboxRun | None:
    return (
        db.query(SandboxRun)
        .filter(SandboxRun.status == SandboxStatus.queued)
        .order_by(SandboxRun.id.asc())
        .first()
    )


async def process_single_run(run_id: int, db: Session) -> None:
    run = db.query(SandboxRun).filter(SandboxRun.id == run_id).first()
    if not run:
        return

    set_correlation_ctx(
        sandbox_run_id=str(run.id),
        worker_name=_WORKER,
        tenant_id=str(run.tenant_id) if run.tenant_id else None,
        scan_id=str(run.scan_id) if run.scan_id else None,
    )

    enqueued_at = getattr(run, "created_at", None)
    if enqueued_at:
        wait_seconds = (time.time() - enqueued_at.timestamp()) if hasattr(enqueued_at, "timestamp") else 0.0
        QUEUE_WAIT_SECONDS.labels(worker=_WORKER).observe(wait_seconds)

    processing_start = time.perf_counter()
    try:
        await execute_sandbox_run(db, run)
        SANDBOX_RUNS_TOTAL.labels(status="completed").inc()
        QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="success").inc()
        logger.info(
            "Sandbox run completed",
            extra={**get_correlation_ctx(), "event": "sandbox_run_completed"},
        )

        # Trigger security alert for high risk sandbox runs
        if run.risk_score is not None and run.risk_score > 0.8:
            create_security_alert(
                db=db,
                tenant_id=run.tenant_id,
                alert_type=SecurityAlertType.SANDBOX_HIGH_RISK,
                severity=AlertSeverity.critical if run.risk_score > 0.9 else AlertSeverity.high,
                url=run.url,
                sandbox_run_id=run.id,
            )
    except Exception as exc:
        SANDBOX_RUNS_TOTAL.labels(status="failed").inc()
        QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="failed").inc()
        WORKER_FAILURES_TOTAL.labels(worker=_WORKER).inc()
        logger.error(
            "Sandbox run failed",
            extra={
                **get_correlation_ctx(),
                "event": "sandbox_execution_error",
                "worker_name": _WORKER,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise
    finally:
        elapsed = time.perf_counter() - processing_start
        QUEUE_PROCESSING_SECONDS.labels(worker=_WORKER).observe(elapsed)


async def worker_loop() -> None:  # pragma: no cover - manual process
    setup_logging()
    init_db()
    logger.info(f"Starting {_WORKER} worker loop")
    set_correlation_ctx(worker_name=_WORKER)
    db = SessionLocal()
    try:
        while True:
            update_worker_heartbeat(_WORKER)

            # Prefer Redis queue if available
            run_id = dequeue_sandbox_run(block=True, timeout=5)
            if run_id is not None:
                QUEUE_DEPTH.labels(worker=_WORKER).dec()
                await process_single_run(run_id, db)
                continue

            # Fallback: poll DB for queued runs
            run = _get_next_queued_run(db)
            if run:
                QUEUE_DEPTH.labels(worker=_WORKER).dec()
                await execute_sandbox_run(db, run)
                continue

            # Nothing to do, sleep briefly
            time.sleep(2)
    finally:
        db.close()


def main() -> None:  # pragma: no cover
    asyncio.run(worker_loop())


if __name__ == "__main__":  # pragma: no cover
    main()
