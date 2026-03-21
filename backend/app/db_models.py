from __future__ import annotations

import enum
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .db import Base


class TenantStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"


class UserRole(str, enum.Enum):
    viewer = "viewer"
    analyst = "analyst"
    engineer = "engineer"
    admin = "admin"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[TenantStatus] = mapped_column(Enum(TenantStatus), default=TenantStatus.active, nullable=False)
    plan_tier: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", cascade="all,delete-orphan")
    api_keys: Mapped[list["APIKey"]] = relationship("APIKey", back_populates="tenant", cascade="all,delete-orphan")
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="tenant", cascade="all,delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="created_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")

    @staticmethod
    def generate_raw_key() -> str:
        return secrets.token_urlsafe(32)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="scans")
    created_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="scans")
    result: Mapped["ScanResult"] = relationship(
        "ScanResult", back_populates="scan", cascade="all,delete-orphan", uselist=False
    )
    scan_metadata: Mapped["ScanMetadata"] = relationship(
        "ScanMetadata", back_populates="scan", cascade="all,delete-orphan", uselist=False
    )


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True)

    prediction: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="result")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_scan_results_confidence_range"),
    )


class ScanMetadata(Base):
    __tablename__ = "scan_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extra: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="scan_metadata")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    action: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    log_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class DomainReputation(Base):
    __tablename__ = "domain_reputation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    domain_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    registrar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whois_privacy_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    flags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ThreatFeedEntry(Base):
    __tablename__ = "threat_feed_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TenantDomainWatch(Base):
    __tablename__ = "tenant_domain_watch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AlertStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    ignored = "ignored"
    resolved = "resolved"


class SecurityAlertType(str, enum.Enum):
    PHISHING_DETECTED = "PHISHING_DETECTED"
    DOMAIN_IMPERSONATION = "DOMAIN_IMPERSONATION"
    SANDBOX_HIGH_RISK = "SANDBOX_HIGH_RISK"
    THREAT_FEED_MATCH = "THREAT_FEED_MATCH"
    CRITICAL_SECURITY_ISSUE = "CRITICAL_SECURITY_ISSUE"


class AlertSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    alert_type: Mapped[SecurityAlertType] = mapped_column(Enum(SecurityAlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)

    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    scan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    sandbox_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sandbox_runs.id", ondelete="SET NULL"), nullable=True)
    security_scan_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("security_scan_runs.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.open, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant")


class NotificationChannelType(str, enum.Enum):
    slack = "slack"
    webhook = "webhook"
    email = "email"


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[NotificationChannelType] = mapped_column(Enum(NotificationChannelType), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant")



class DomainImpersonationAlert(Base):
    __tablename__ = "domain_impersonation_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    suspicious_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    detection_type: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    enrichment: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.open, nullable=False)


class SandboxStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class SandboxRun(Base):
    __tablename__ = "sandbox_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    scan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SandboxStatus] = mapped_column(Enum(SandboxStatus), default=SandboxStatus.queued, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifacts_location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class SandboxEvent(Base):
    __tablename__ = "sandbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sandbox_run_id: Mapped[int] = mapped_column(ForeignKey("sandbox_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)


class SandboxArtifact(Base):
    __tablename__ = "sandbox_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sandbox_run_id: Mapped[int] = mapped_column(ForeignKey("sandbox_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SecurityScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class SecurityIssueSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SecurityScanRun(Base):
    __tablename__ = "security_scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SecurityScanStatus] = mapped_column(Enum(SecurityScanStatus), default=SecurityScanStatus.queued, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    issues: Mapped[list["SecurityScanIssue"]] = relationship("SecurityScanIssue", back_populates="run", cascade="all,delete-orphan")
    artifacts: Mapped[list["SecurityScanArtifact"]] = relationship("SecurityScanArtifact", back_populates="run", cascade="all,delete-orphan")


class SecurityScanIssue(Base):
    __tablename__ = "security_scan_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("security_scan_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    severity: Mapped[SecurityIssueSeverity] = mapped_column(Enum(SecurityIssueSeverity), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False) 
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    run: Mapped["SecurityScanRun"] = relationship("SecurityScanRun", back_populates="issues")


class SecurityScanArtifact(Base):
    __tablename__ = "security_scan_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("security_scan_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    run: Mapped["SecurityScanRun"] = relationship("SecurityScanRun", back_populates="artifacts")


class BrandTemplate(Base):
    __tablename__ = "brand_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    brand_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    legitimate_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_vector = mapped_column(Vector(512), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    login_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

