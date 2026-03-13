from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import (
    DomainReputation,
    DomainImpersonationAlert,
    TenantDomainWatch,
    AlertStatus,
    UserRole,
)
from .dependencies import CurrentTenant, require_role
from .services.domain_intel import calculate_domain_risk
from .schemas_saas import (
    DomainIntelResponse,
    DomainWatchCreateRequest,
    DomainWatchResponse,
    ImpersonationAlertResponse,
)


router = APIRouter(prefix="/intel", tags=["intel"])


@router.get("/domain/{domain}", response_model=DomainIntelResponse)
def get_domain_intel(domain: str, db: Session = Depends(get_db)):
    # Normalize domain to lower-case
    domain_l = domain.lower()
    repo = db.query(DomainReputation).filter(DomainReputation.domain == domain_l).first()
    if not repo:
        # Compute on-demand; this will also create a DomainReputation row.
        risk_score, _reasons = calculate_domain_risk(db, domain_l)
        repo = db.query(DomainReputation).filter(DomainReputation.domain == domain_l).first()
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    return DomainIntelResponse(
        domain=repo.domain,
        risk_score=repo.risk_score,
        domain_age_days=repo.domain_age_days,
        registrar=repo.registrar,
        whois_privacy_enabled=repo.whois_privacy_enabled,
        flags=repo.flags or {},
        first_seen_at=repo.first_seen_at,
        last_seen_at=repo.last_seen_at,
    )


@router.get("/impersonation-alerts", response_model=List[ImpersonationAlertResponse])
def list_impersonation_alerts(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    status_filter: Optional[AlertStatus] = Query(None, alias="status"),
):
    q = db.query(DomainImpersonationAlert).filter(DomainImpersonationAlert.tenant_id == tenant.id)
    if status_filter is not None:
        q = q.filter(DomainImpersonationAlert.status == status_filter)
    alerts = q.order_by(DomainImpersonationAlert.created_at.desc()).limit(200).all()
    return alerts


@router.get("/watch-domain", response_model=List[DomainWatchResponse])
def list_watch_domains(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    watches = (
        db.query(TenantDomainWatch)
        .filter(TenantDomainWatch.tenant_id == tenant.id)
        .order_by(TenantDomainWatch.created_at.desc())
        .all()
    )
    return watches


@router.post(
    "/watch-domain",
    response_model=DomainWatchResponse,
    dependencies=[Depends(require_role(UserRole.analyst))],
)
def create_watch_domain(
    payload: DomainWatchCreateRequest,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    watch = TenantDomainWatch(
        tenant_id=tenant.id,
        domain=payload.domain.lower(),
        brand_name=payload.brand_name,
    )
    db.add(watch)
    db.commit()
    db.refresh(watch)
    return watch


@router.delete(
    "/watch-domain/{watch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.analyst))],
)
def delete_watch_domain(
    watch_id: int,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    watch = (
        db.query(TenantDomainWatch)
        .filter(TenantDomainWatch.id == watch_id, TenantDomainWatch.tenant_id == tenant.id)
        .first()
    )
    if not watch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch domain not found")
    db.delete(watch)
    db.commit()
    return

