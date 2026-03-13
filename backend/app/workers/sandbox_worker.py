"""
Sandbox worker.

This worker consumes sandbox run jobs (via Redis queue when available or by
polling the database) and executes them using the sandbox runner.
"""

from __future__ import annotations

import asyncio
import time

from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..db_models import SandboxRun, SandboxStatus
from ..sandbox.queue import dequeue_sandbox_run
from ..sandbox.runner import execute_sandbox_run


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
    await execute_sandbox_run(db, run)


async def worker_loop() -> None:  # pragma: no cover - manual process
    init_db()
    db = SessionLocal()
    try:
        while True:
            # Prefer Redis queue if available
            run_id = dequeue_sandbox_run(block=True, timeout=5)
            if run_id is not None:
                await process_single_run(run_id, db)
                continue

            # Fallback: poll DB for queued runs
            run = _get_next_queued_run(db)
            if run:
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

