from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from .db import get_db
from .db_models import User
from .dependencies import get_current_user
from .ml.predictor import Predictor

router = APIRouter(prefix="/predict", tags=["prediction"])

predictor = Predictor()

@router.post("/")
def get_prediction(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Production serving endpoint for phishing prediction.
    Input: { "url": "...", "html": "...", "metadata": { ... } }
    Output: { "label": "phishing/safe", "confidence": 0.92, "version": "v1", "reasons": [...] }
    """
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
        
    html = data.get("html")
    metadata = data.get("metadata", {})
    
    # ML model prediction
    results = predictor.predict(db, url, html, metadata)
    
    return results
