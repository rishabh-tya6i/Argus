from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import User, UserRole
from .dependencies import CurrentTenant, require_role
from .schemas_saas import UserResponse, UserCreateRequest
from .security import hash_password


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_role(UserRole.admin))])
def list_users(tenant: CurrentTenant, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.tenant_id == tenant.id).order_by(User.id).all()
    return users


@router.post("", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.admin))])
def create_user(
    payload: UserCreateRequest,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.admin))])
def delete_user(
    user_id: int,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return

