from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import User, Tenant, APIKey, UserRole
from .security import decode_token, verify_api_key, role_at_least


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    Resolve the current user from a JWT bearer token if present.

    This is intentionally permissive (returns None if unauthenticated) so that
    endpoints like /api/predict can run in anonymous mode but still attach
    tenant context when authentication is provided.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = int(payload.get("sub"))
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Attach to request for downstream access (e.g., rate limiting)
    request.state.user = user
    request.state.tenant_id = user.tenant_id
    return user


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_current_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def get_api_key_context(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[APIKey]:
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return None

    # For security, we only store a hash; we use a prefix for lookup.
    prefix = api_key_header[:16]
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_prefix == prefix, APIKey.is_active.is_(True))
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if not verify_api_key(api_key_header, api_key.key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    request.state.api_key = api_key
    request.state.tenant_id = api_key.tenant_id
    return api_key


def require_role(required: UserRole):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]

