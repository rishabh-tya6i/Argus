from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
import bcrypt

from .db_models import User, APIKey, UserRole

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRES_MIN = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MIN", "60"))
JWT_REFRESH_TOKEN_EXPIRES_MIN = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_MIN", "7")) * 24 * 60

API_KEY_HASH_SECRET = os.getenv("API_KEY_HASH_SECRET", JWT_SECRET)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


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
    # Derive a stable hash combined with an application-level secret.
    # Note: bcrypt has a 72 byte limit for passwords.
    secret_key = (API_KEY_HASH_SECRET + raw_key)[:72]
    return bcrypt.hashpw(secret_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    try:
        secret_key = (API_KEY_HASH_SECRET + raw_key)[:72]
        return bcrypt.checkpw(secret_key.encode("utf-8"), key_hash.encode("utf-8"))
    except Exception:
        return False


def extract_api_key_prefix(raw_key: str) -> str:
    return raw_key[:16]


def role_at_least(actual: UserRole, required: UserRole) -> bool:
    order = [UserRole.viewer, UserRole.analyst, UserRole.engineer, UserRole.admin]
    return order.index(actual) >= order.index(required)

