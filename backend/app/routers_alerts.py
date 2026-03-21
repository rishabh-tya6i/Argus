from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import SecurityAlert, AlertStatus, AlertSeverity, SecurityAlertType
from .dependencies import get_current_active_user
from .schemas_saas import SecurityAlertResponse, AlertStatusUpdate, UserResponse
from .observability import ALERTS_BY_SEVERITY

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=List[SecurityAlertResponse])
async def get_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    alert_type: Optional[SecurityAlertType] = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Get all security alerts for the current tenant, with optional filtering.
    """
    query = db.query(SecurityAlert).filter(SecurityAlert.tenant_id == current_user.tenant_id)

    if status:
        query = query.filter(SecurityAlert.status == status)
    if severity:
        query = query.filter(SecurityAlert.severity == severity)
    if alert_type:
        query = query.filter(SecurityAlert.alert_type == alert_type)

    return query.order_by(SecurityAlert.created_at.desc()).all()


@router.get("/{alert_id}", response_model=SecurityAlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Get a single security alert by ID.
    """
    alert = (
        db.query(SecurityAlert)
        .filter(
            SecurityAlert.id == alert_id,
            SecurityAlert.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.patch("/{alert_id}/status", response_model=SecurityAlertResponse)
async def update_alert_status(
    alert_id: int,
    status_update: AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Update the status of a security alert.
    """
    alert = (
        db.query(SecurityAlert)
        .filter(
            SecurityAlert.id == alert_id,
            SecurityAlert.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update metric if status is changing from open to something else
    if alert.status == AlertStatus.open and status_update.status != AlertStatus.open:
        ALERTS_BY_SEVERITY.labels(severity=alert.severity.value).dec()
    elif alert.status != AlertStatus.open and status_update.status == AlertStatus.open:
        ALERTS_BY_SEVERITY.labels(severity=alert.severity.value).inc()

    alert.status = status_update.status
    db.commit()
    db.refresh(alert)

    # Optional: If alert is resolved, notify linked cases
    if alert.status == AlertStatus.resolved:
        from .services import case_service
        for mapping in alert.case_mappings:
            case_service.add_comment(
                db,
                alert.tenant_id,
                current_user.id,
                mapping.case_id,
                f"Linked Alert ID {alert.id} was resolved. Status: {alert.status.value}",
            )

    return alert
