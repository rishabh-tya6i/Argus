from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import UserRole
from .dependencies import CurrentTenant, require_role
from .schemas_saas import TenantResponse, TenantConfigUpdate


router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("", response_model=TenantResponse)
def get_tenant(tenant: CurrentTenant):
    return tenant


@router.patch("/config", response_model=TenantResponse, dependencies=[Depends(require_role(UserRole.admin))])
def update_tenant_config(
    payload: TenantConfigUpdate,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    tenant.config = payload.config
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

