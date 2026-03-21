from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..db_models import SecurityAlert, SecurityAlertType, AlertSeverity, AlertStatus
from .alert_queue import enqueue_alert_dispatch
from ..observability import ALERTS_GENERATED_TOTAL, ALERTS_BY_SEVERITY

logger = logging.getLogger(__name__)


def create_security_alert(
    db: Session,
    tenant_id: int,
    alert_type: SecurityAlertType,
    severity: AlertSeverity,
    url: Optional[str] = None,
    domain: Optional[str] = None,
    scan_id: Optional[int] = None,
    sandbox_run_id: Optional[int] = None,
    security_scan_run_id: Optional[int] = None,
) -> SecurityAlert:
    """
    Creates a new security alert record and enqueues it for notification dispatch.
    """
    alert = SecurityAlert(
        tenant_id=tenant_id,
        alert_type=alert_type,
        severity=severity,
        url=url,
        domain=domain,
        scan_id=scan_id,
        sandbox_run_id=sandbox_run_id,
        security_scan_run_id=security_scan_run_id,
        created_at=datetime.utcnow(),
        status=AlertStatus.open,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Log creation
    logger.info(
        f"Security alert created: ID={alert.id}, Tenant={tenant_id}, Type={alert_type}, Severity={severity}",
        extra={
            "event": "security_alert_created",
            "alert_id": alert.id,
            "tenant_id": tenant_id,
            "alert_type": alert_type,
            "severity": severity,
        },
    )

    # Increment metrics
    ALERTS_GENERATED_TOTAL.labels(alert_type=alert_type.value, severity=severity.value).inc()
    ALERTS_BY_SEVERITY.labels(severity=severity.value).inc()

    # Enqueue for dispatch
    enqueue_alert_dispatch(alert.id)

    return alert
