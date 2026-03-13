from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from .db_models import UserRole, TenantStatus, AlertStatus, SandboxStatus


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


class DomainIntelResponse(BaseModel):
    domain: str
    risk_score: float
    domain_age_days: Optional[int]
    registrar: Optional[str]
    whois_privacy_enabled: Optional[bool]
    flags: Dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime


class DomainWatchCreateRequest(BaseModel):
    domain: str
    brand_name: str


class DomainWatchResponse(BaseModel):
    id: int
    domain: str
    brand_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ImpersonationAlertResponse(BaseModel):
    id: int
    tenant_id: int
    brand_name: str
    suspicious_domain: str
    detection_type: str
    risk_score: float
    created_at: datetime
    status: AlertStatus

    class Config:
        from_attributes = True


class SandboxRunCreateRequest(BaseModel):
    url: str
    scan_id: Optional[int] = None


class SandboxRunResponse(BaseModel):
    id: int
    tenant_id: int
    scan_id: Optional[int]
    url: str
    status: SandboxStatus
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    risk_score: Optional[float]
    summary: Optional[str]
    artifacts_location: Optional[str]

    class Config:
        from_attributes = True


class SandboxEventResponse(BaseModel):
    id: int
    sandbox_run_id: int
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]

    class Config:
        from_attributes = True
