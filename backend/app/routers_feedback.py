from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from .db import get_db
from .db_models import ScanFeedback, User, UserRole, Scan, FeedbackLabel
from .schemas_saas import ScanFeedbackCreateRequest, ScanFeedbackResponse, ScanFeedbackAggregatedResponse
from .dependencies import get_current_user, require_role
from .observability import ML_FEEDBACK_COUNT

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/", response_model=ScanFeedbackResponse)
def create_feedback(
    feedback_in: ScanFeedbackCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.analyst)),
):
    scan = db.query(Scan).filter(Scan.id == feedback_in.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check if feedback already exists for this analyst and scan
    existing_feedback = db.query(ScanFeedback).filter(
        ScanFeedback.scan_id == feedback_in.scan_id,
        ScanFeedback.analyst_user_id == current_user.id
    ).first()
    
    if existing_feedback:
        existing_feedback.label = feedback_in.label
        existing_feedback.notes = feedback_in.notes
        db.commit()
        db.refresh(existing_feedback)
        
        # Update metrics
        ML_FEEDBACK_COUNT.labels(label=feedback_in.label.value).inc()
        
        return existing_feedback
    
    feedback = ScanFeedback(
        scan_id=feedback_in.scan_id,
        tenant_id=current_user.tenant_id,
        analyst_user_id=current_user.id,
        label=feedback_in.label,
        notes=feedback_in.notes
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    # Update metrics
    ML_FEEDBACK_COUNT.labels(label=feedback_in.label.value).inc()
    
    return feedback

@router.get("/", response_model=List[ScanFeedbackResponse])
def get_feedback(
    scan_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ScanFeedback)
    
    if scan_id:
        query = query.filter(ScanFeedback.scan_id == scan_id)
    if tenant_id:
        if current_user.role != UserRole.admin and tenant_id != current_user.tenant_id:
             raise HTTPException(status_code=403, detail="Access denied to other tenant's feedback")
        query = query.filter(ScanFeedback.tenant_id == tenant_id)
    else:
        if current_user.role != UserRole.admin:
            query = query.filter(ScanFeedback.tenant_id == current_user.tenant_id)

    return query.all()

@router.get("/aggregated", response_model=List[ScanFeedbackAggregatedResponse])
def get_aggregated_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Restrict to admin/engineer for system-wide training? 
    # Or just return for user's tenant context?
    # The requirement says "return majority label per scan (for training)".
    # Usually training happens across all data if possible, or per tenant.
    
    results = db.query(
        ScanFeedback.scan_id,
        ScanFeedback.label,
        func.count(ScanFeedback.id).label('count')
    ).group_by(ScanFeedback.scan_id, ScanFeedback.label).all()
    
    aggregated = {}
    for scan_id, label, count in results:
        if scan_id not in aggregated:
            aggregated[scan_id] = []
        aggregated[scan_id].append({'label': label, 'count': count})
    
    final_results = []
    for scan_id, feedback_list in aggregated.items():
        majority = max(feedback_list, key=lambda x: x['count'])
        total_count = sum(f['count'] for f in feedback_list)
        final_results.append(ScanFeedbackAggregatedResponse(
            scan_id=scan_id,
            majority_label=majority['label'],
            feedback_count=total_count,
            confidence=majority['count'] / total_count
        ))
        
    return final_results
