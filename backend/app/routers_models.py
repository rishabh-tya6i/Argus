from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import ModelVersion, User, UserRole
from .schemas_saas import ModelVersionResponse, ModelActivateRequest
from .dependencies import get_current_user, require_role

router = APIRouter(prefix="/models", tags=["models"])

@router.get("/", response_model=List[ModelVersionResponse])
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (current_user.role == UserRole.engineer or current_user.role == UserRole.admin):
         raise HTTPException(status_code=403, detail="Only engineers/admins can manage models")
    return db.query(ModelVersion).all()

@router.post("/{model_id}/activate", response_model=ModelVersionResponse)
def activate_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.engineer)),
):
    model = db.get(ModelVersion, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found")
    
    # Deactivate other active models of the same model_name
    db.query(ModelVersion).filter(
        ModelVersion.model_name == model.model_name,
        ModelVersion.is_active == True
    ).update({"is_active": False})
    
    model.is_active = True
    db.commit()
    db.refresh(model)
    return model
