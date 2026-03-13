from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from .db_models import UserRole, TenantStatus


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    tenant_name: str
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: TenantStatus
    plan_tier: Optional[str]
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantConfigUpdate(BaseModel):
    config: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.viewer


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: Optional[str] = None


class APIKeyCreateResponse(BaseModel):
    api_key: str
    api_key_record: APIKeyResponse


class ScanSummaryResponse(BaseModel):
    id: int
    url: str
    source: Optional[str]
    created_at: datetime
    prediction: str
    confidence: float


class ScanDetailResponse(BaseModel):
    id: int
    url: str
    source: Optional[str]
    created_at: datetime
    prediction: str
    confidence: float
    explanation: Dict[str, Any]
    client_type: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]

