from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from passlib.context import CryptContext

from .db_models import User, APIKey, UserRole


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRES_MIN = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MIN", "60"))
JWT_REFRESH_TOKEN_EXPIRES_MIN = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_MIN", "7")) * 24 * 60

API_KEY_HASH_SECRET = os.getenv("API_KEY_HASH_SECRET", JWT_SECRET)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_REFRESH_TOKEN_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def hash_api_key(raw_key: str) -> str:
    # Derive a stable hash using the same password hashing context for simplicity
    # combined with an application-level secret.
    return pwd_context.hash(API_KEY_HASH_SECRET + raw_key)


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return pwd_context.verify(API_KEY_HASH_SECRET + raw_key, key_hash)


def extract_api_key_prefix(raw_key: str) -> str:
    return raw_key[:16]


def role_at_least(actual: UserRole, required: UserRole) -> bool:
    order = [UserRole.viewer, UserRole.analyst, UserRole.engineer, UserRole.admin]
    return order.index(actual) >= order.index(required)

