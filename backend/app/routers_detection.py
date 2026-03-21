from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import time

from .db import get_db
from .db_models import User
from .dependencies import get_current_user
from .detection.orchestrator import DetectionOrchestrator

router = APIRouter(prefix="/detect", tags=["detection"])

orchestrator = DetectionOrchestrator()

@router.post("/")
async def run_detection(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advanced hybrid phishing detection engine endpoint.
    Combines ML, rule-based heuristics, and threat intelligence.
    
    Input: { "url": "...", "html": "...", "metadata": { ... } }
    Output: { 
        "label": "phishing/suspicious/safe", 
        "confidence": 0.95, 
        "breakdown": { "ml": ..., "rules": ..., "threat_intel": ... },
        "reasons": [...] 
    }
    """
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
        
    html = data.get("html")
    metadata = data.get("metadata", {})
    
    # Run the detection orchestrator
    try:
        results = await orchestrator.detect(db, url, html, metadata)
        return results
    except Exception as e:
        # In production, we'd log the full error for observability
        # Here we return a descriptive error message
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@router.get("/threat-check")
async def check_threat_intel(
    url: str,
    ip: Optional[str] = None,
    sender: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Direct endpoint for checking threat intelligence indicators.
    """
    try:
        results = await orchestrator.threat_intel.check(url, ip, sender)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
