from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import UserRole, CaseStatus, AlertSeverity
from .dependencies import CurrentTenant, CurrentUser, require_role
from .schemas_saas import (
    InvestigationCaseResponse,
    CaseCreateRequest,
    CaseUpdateRequest,
    CaseCommentResponse,
    CaseCommentCreateRequest,
    CaseLinkAlertsRequest,
    CaseStatusUpdateRequest,
    CaseAssignRequest,
    SecurityAlertResponse,
)
from .services import case_service

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=InvestigationCaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreateRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer cannot create cases")
    
    case = case_service.create_case(
        db,
        tenant.id,
        user.id,
        payload.title,
        payload.severity,
        payload.description,
        payload.alert_ids,
    )
    return case


@router.get("", response_model=List[InvestigationCaseResponse])
def list_cases(
    tenant: CurrentTenant,
    status: Optional[CaseStatus] = None,
    severity: Optional[AlertSeverity] = None,
    assigned_to: Optional[int] = None,
    db: Session = Depends(get_db),
):
    cases = case_service.list_cases(
        db,
        tenant.id,
        status=status,
        severity=severity,
        assigned_to_user_id=assigned_to,
    )
    return cases


@router.get("/{case_id}", response_model=InvestigationCaseResponse)
def get_case(
    case_id: int,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    case = case_service.get_case(db, tenant.id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Manually form alerts list from mappings
    # Since we can't easily do it via pydantic with multiple layers of nesting and aliasing
    # if it's not pre-fetched in a friendly way
    res = InvestigationCaseResponse.from_orm(case)
    res.alerts = [m.alert for m in case.alert_mappings]
    return res


@router.patch("/{case_id}", response_model=InvestigationCaseResponse)
def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer cannot update cases")
    
    # Engineer/Analyst check
    if user.role == UserRole.analyst and payload.assigned_to_user_id is not None:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analysts cannot reassign cases")

    case = case_service.update_case(
        db,
        tenant.id,
        user.id,
        case_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        status=payload.status,
        assigned_to_user_id=payload.assigned_to_user_id,
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    res = InvestigationCaseResponse.from_orm(case)
    res.alerts = [m.alert for m in case.alert_mappings]
    return res


@router.post("/{case_id}/assign", response_model=InvestigationCaseResponse)
def assign_case(
    case_id: int,
    payload: CaseAssignRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role not in [UserRole.engineer, UserRole.admin]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only engineers and admins can assign cases")
    
    case = case_service.update_case(
        db,
        tenant.id,
        user.id,
        case_id,
        assigned_to_user_id=payload.user_id,
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    res = InvestigationCaseResponse.from_orm(case)
    res.alerts = [m.alert for m in case.alert_mappings]
    return res


@router.post("/{case_id}/status", response_model=InvestigationCaseResponse)
def update_case_status(
    case_id: int,
    payload: CaseStatusUpdateRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer cannot change status")
    
    case = case_service.update_case(
        db,
        tenant.id,
        user.id,
        case_id,
        status=payload.status,
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    res = InvestigationCaseResponse.from_orm(case)
    res.alerts = [m.alert for m in case.alert_mappings]
    return res


@router.post("/{case_id}/comments", response_model=CaseCommentResponse)
def add_comment(
    case_id: int,
    payload: CaseCommentCreateRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer cannot comment")
    
    # Check if case exists
    case = case_service.get_case(db, tenant.id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    comment = case_service.add_comment(
        db,
        tenant.id,
        user.id,
        case_id,
        payload.comment,
    )
    return comment


@router.get("/{case_id}/comments", response_model=List[CaseCommentResponse])
def get_comments(
    case_id: int,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    # Check if case exists
    case = case_service.get_case(db, tenant.id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    comments = case_service.get_comments(db, case_id)
    return comments


@router.post("/{case_id}/alerts", status_code=status.HTTP_204_NO_CONTENT)
def link_alerts(
    case_id: int,
    payload: CaseLinkAlertsRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer cannot link alerts")
    
    case = case_service.get_case(db, tenant.id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_service.link_alerts(
        db,
        tenant.id,
        user.id,
        case_id,
        payload.alert_ids,
    )
    return
