from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import SandboxRun, SandboxEvent, SandboxStatus, Scan, UserRole
from .dependencies import CurrentTenant, require_role
from .sandbox.queue import enqueue_sandbox_run
from .schemas_saas import SandboxRunCreateRequest, SandboxRunResponse, SandboxEventResponse


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/run", response_model=SandboxRunResponse, dependencies=[Depends(require_role(UserRole.analyst))])
def start_sandbox_run(
    payload: SandboxRunCreateRequest,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    scan_id = None
    if payload.scan_id is not None:
        scan = db.query(Scan).filter(Scan.id == payload.scan_id, Scan.tenant_id == tenant.id).first()
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found for this tenant")
        scan_id = scan.id

    run = SandboxRun(
        tenant_id=tenant.id,
        scan_id=scan_id,
        url=payload.url,
        status=SandboxStatus.queued,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    enqueue_sandbox_run(run.id)

    return run


@router.get("/runs", response_model=List[SandboxRunResponse])
def list_sandbox_runs(tenant: CurrentTenant, url: str | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(SandboxRun)
        .filter(SandboxRun.tenant_id == tenant.id)
    )
    if url:
        query = query.filter(SandboxRun.url == url)
    
    runs = query.order_by(SandboxRun.id.desc()).limit(100).all()
    return runs


@router.get("/runs/{run_id}", response_model=SandboxRunResponse)
def get_sandbox_run(run_id: int, tenant: CurrentTenant, db: Session = Depends(get_db)):
    run = (
        db.query(SandboxRun)
        .filter(SandboxRun.id == run_id, SandboxRun.tenant_id == tenant.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox run not found")
    return run


@router.get("/runs/{run_id}/events", response_model=List[SandboxEventResponse])
def get_sandbox_events(run_id: int, tenant: CurrentTenant, db: Session = Depends(get_db)):
    run = (
        db.query(SandboxRun)
        .filter(SandboxRun.id == run_id, SandboxRun.tenant_id == tenant.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox run not found")

    events = (
        db.query(SandboxEvent)
        .filter(SandboxEvent.sandbox_run_id == run.id)
        .order_by(SandboxEvent.timestamp.asc())
        .all()
    )
    return events

