from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import SecurityScanRun, SecurityScanStatus, UserRole
from .dependencies import CurrentTenant, require_role
from .security_scanner.queue import enqueue_security_scan
from .schemas_saas import SecurityScanCreateRequest, SecurityScanResponse


router = APIRouter(prefix="/security-scans", tags=["security-scans"])


@router.post("", response_model=SecurityScanResponse, dependencies=[Depends(require_role(UserRole.analyst))])
def create_security_scan(
    payload: SecurityScanCreateRequest,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    run = SecurityScanRun(
        tenant_id=tenant.id,
        url=payload.url,
        status=SecurityScanStatus.queued,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    enqueue_security_scan(run.id)

    return run


@router.get("", response_model=List[SecurityScanResponse])
def list_security_scans(tenant: CurrentTenant, url: str | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(SecurityScanRun)
        .filter(SecurityScanRun.tenant_id == tenant.id)
    )
    if url:
        query = query.filter(SecurityScanRun.url == url)
    
    runs = query.order_by(SecurityScanRun.id.desc()).limit(100).all()
    return runs


@router.get("/{scan_id}", response_model=SecurityScanResponse)
def get_security_scan(scan_id: int, tenant: CurrentTenant, db: Session = Depends(get_db)):
    run = (
        db.query(SecurityScanRun)
        .filter(SecurityScanRun.id == scan_id, SecurityScanRun.tenant_id == tenant.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security scan not found")
    return run
