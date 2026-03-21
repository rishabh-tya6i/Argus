from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from ..db_models import (
    InvestigationCase,
    CaseAlertMapping,
    CaseComment,
    SecurityAlert,
    User,
    AlertSeverity,
    CaseStatus,
    AuditLog,
)
from ..observability import (
    CASES_CREATED_TOTAL,
    CASES_RESOLVED_TOTAL,
    CASE_RESOLUTION_TIME,
)

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    tenant_id: int,
    user_id: Optional[int],
    action: str,
    metadata: Dict[str, Any],
) -> None:
    audit_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        log_metadata=metadata,
        created_at=datetime.utcnow(),
    )
    db.add(audit_entry)
    # Don't commit here, let the caller commit if needed or it will be part of the transaction


def create_case(
    db: Session,
    tenant_id: int,
    created_by_user_id: int,
    title: str,
    severity: AlertSeverity,
    description: Optional[str] = None,
    alert_ids: Optional[List[int]] = None,
) -> InvestigationCase:
    case = InvestigationCase(
        tenant_id=tenant_id,
        created_by_user_id=created_by_user_id,
        title=title,
        description=description,
        severity=severity,
        status=CaseStatus.open,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(case)
    db.flush()  # Get case ID

    if alert_ids:
        for alert_id in alert_ids:
            mapping = CaseAlertMapping(case_id=case.id, alert_id=alert_id)
            db.add(mapping)

    log_audit(
        db,
        tenant_id,
        created_by_user_id,
        "case_created",
        {"case_id": case.id, "title": title, "alert_ids": alert_ids or []},
    )

    CASES_CREATED_TOTAL.labels(severity=severity.value).inc()

    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, tenant_id: int, case_id: int) -> Optional[InvestigationCase]:
    return (
        db.query(InvestigationCase)
        .options(
            joinedload(InvestigationCase.assigned_to),
            joinedload(InvestigationCase.created_by),
            joinedload(InvestigationCase.alert_mappings).joinedload(CaseAlertMapping.alert),
        )
        .filter(InvestigationCase.id == case_id, InvestigationCase.tenant_id == tenant_id)
        .first()
    )


def list_cases(
    db: Session,
    tenant_id: int,
    status: Optional[CaseStatus] = None,
    severity: Optional[AlertSeverity] = None,
    assigned_to_user_id: Optional[int] = None,
) -> List[InvestigationCase]:
    query = db.query(InvestigationCase).filter(InvestigationCase.tenant_id == tenant_id)

    if status:
        query = query.filter(InvestigationCase.status == status)
    if severity:
        query = query.filter(InvestigationCase.severity == severity)
    if assigned_to_user_id is not None:
        query = query.filter(InvestigationCase.assigned_to_user_id == assigned_to_user_id)

    return (
        query.options(
            joinedload(InvestigationCase.assigned_to),
            joinedload(InvestigationCase.created_by),
        )
        .order_by(InvestigationCase.created_at.desc())
        .all()
    )


def update_case(
    db: Session,
    tenant_id: int,
    user_id: int,
    case_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    status: Optional[CaseStatus] = None,
    assigned_to_user_id: Optional[int] = None,
) -> Optional[InvestigationCase]:
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id, InvestigationCase.tenant_id == tenant_id).first()
    if not case:
        return None

    changes = {}
    if title is not None:
        changes["title"] = {"old": case.title, "new": title}
        case.title = title
    if description is not None:
        changes["description"] = {"old": case.description, "new": description}
        case.description = description
    if severity is not None:
        changes["severity"] = {"old": case.severity.value, "new": severity.value}
        case.severity = severity
    
    if status is not None and status != case.status:
        changes["status"] = {"old": case.status.value, "new": status.value}
        
        # If transitioning to resolved/closed, track metrics
        if status in [CaseStatus.resolved, CaseStatus.closed] and case.status not in [CaseStatus.resolved, CaseStatus.closed]:
            duration = (datetime.utcnow() - case.created_at).total_seconds()
            CASE_RESOLUTION_TIME.labels(severity=case.severity.value).observe(duration)
            if status == CaseStatus.resolved:
                CASES_RESOLVED_TOTAL.labels(severity=case.severity.value).inc()
        
        case.status = status

    if assigned_to_user_id is not None or "assigned_to_user_id" in changes: # Special case for nullable
        if assigned_to_user_id != case.assigned_to_user_id:
            changes["assigned_to_user_id"] = {"old": case.assigned_to_user_id, "new": assigned_to_user_id}
            case.assigned_to_user_id = assigned_to_user_id

    if changes:
        case.updated_at = datetime.utcnow()
        log_audit(db, tenant_id, user_id, "case_updated", {"case_id": case_id, "changes": changes})
        db.commit()
        db.refresh(case)

    return case


def add_comment(
    db: Session,
    tenant_id: int,
    user_id: int,
    case_id: int,
    comment_text: str,
) -> CaseComment:
    comment = CaseComment(
        case_id=case_id,
        user_id=user_id,
        comment=comment_text,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    
    log_audit(db, tenant_id, user_id, "comment_added", {"case_id": case_id, "comment_id": comment.id})
    
    db.commit()
    db.refresh(comment)
    return comment


def get_comments(db: Session, case_id: int) -> List[CaseComment]:
    return (
        db.query(CaseComment)
        .options(joinedload(CaseComment.user))
        .filter(CaseComment.case_id == case_id)
        .order_by(CaseComment.created_at.asc())
        .all()
    )


def link_alerts(
    db: Session,
    tenant_id: int,
    user_id: int,
    case_id: int,
    alert_ids: List[int],
) -> None:
    for alert_id in alert_ids:
        # Check if already linked
        existing = db.query(CaseAlertMapping).filter(CaseAlertMapping.case_id == case_id, CaseAlertMapping.alert_id == alert_id).first()
        if not existing:
            mapping = CaseAlertMapping(case_id=case_id, alert_id=alert_id)
            db.add(mapping)
    
    log_audit(db, tenant_id, user_id, "alerts_linked", {"case_id": case_id, "alert_ids": alert_ids})
    db.commit()
