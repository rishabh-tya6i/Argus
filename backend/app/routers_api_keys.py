from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import APIKey, UserRole
from .dependencies import CurrentTenant, require_role
from .schemas_saas import APIKeyResponse, APIKeyCreateRequest, APIKeyCreateResponse
from .security import hash_api_key, extract_api_key_prefix


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[APIKeyResponse], dependencies=[Depends(require_role(UserRole.engineer))])
def list_api_keys(tenant: CurrentTenant, db: Session = Depends(get_db)):
    keys = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).order_by(APIKey.id).all()
    return keys


@router.post("", response_model=APIKeyCreateResponse, dependencies=[Depends(require_role(UserRole.engineer))])
def create_api_key(
    payload: APIKeyCreateRequest,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    raw_key = APIKey.generate_raw_key()
    key_hash = hash_api_key(raw_key)
    prefix = extract_api_key_prefix(raw_key)

    record = APIKey(
        tenant_id=tenant.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=payload.scopes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return APIKeyCreateResponse(api_key=raw_key, api_key_record=record)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.engineer))])
def delete_api_key(
    api_key_id: int,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == api_key_id, APIKey.tenant_id == tenant.id)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db.delete(api_key)
    db.commit()
    return

