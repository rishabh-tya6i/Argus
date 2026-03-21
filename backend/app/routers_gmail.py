from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from .db import get_db
from .dependencies import CurrentTenant, get_current_user_optional
from .schemas import EmailScanResponse, SyncGmailRequest
from .services.gmail_service import GmailService
from .db_models import EmailScan

router = APIRouter(tags=["gmail"])

@router.post("/gmail/sync", response_model=List[EmailScanResponse])
async def sync_gmail(
    req: SyncGmailRequest,
    tenant: CurrentTenant,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Manually trigger a Gmail sync and scan.
    """
    user = getattr(request.state, "user", None)
    if not user:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User context required")
    
    # In a real app, you'd get the real gmail_api_client from a credential store
    gmail_scans = await GmailService.fetch_and_scan_emails(
        db=db,
        tenant_id=tenant.id,
        user_id=user.id,
        gmail_api_client=None # Mocked in service
    )
    
    return gmail_scans

@router.get("/gmail/scans", response_model=List[EmailScanResponse])
async def get_gmail_scans(
    tenant: CurrentTenant,
    db: Session = Depends(get_db)
):
    """
    List historical Gmail scans for the current tenant.
    """
    scans = db.query(EmailScan).filter(EmailScan.tenant_id == tenant.id).order_by(EmailScan.created_at.desc()).limit(100).all()
    return scans
