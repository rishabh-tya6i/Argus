"""
Threat intelligence ingestion worker.

This module provides a simple framework for ingesting external phishing /
threat feeds into the DomainReputation and ThreatFeedEntry tables.

In production this would be scheduled (e.g. via cron, Celery, or a Kubernetes
CronJob) and configured with real feed sources. Here we provide a pluggable
interface and basic upsert logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from sqlalchemy.orm import Session

from ..db import SessionLocal, init_db
from ..db_models import DomainReputation, ThreatFeedEntry, TenantDomainWatch, DomainImpersonationAlert, AlertStatus
from ..services.domain_intel import detect_typosquatting, detect_homograph


@dataclass
class ThreatFeedRecord:
    domain: str
    source: str
    threat_type: str
    confidence: float = 1.0


class ThreatFeedSource:
    """Abstract interface for threat feed sources."""

    def fetch(self) -> Iterable[ThreatFeedRecord]:  # pragma: no cover - interface
        raise NotImplementedError


def upsert_threat_entry(db: Session, record: ThreatFeedRecord) -> None:
    existing = (
        db.query(ThreatFeedEntry)
        .filter(
            ThreatFeedEntry.domain == record.domain,
            ThreatFeedEntry.source == record.source,
            ThreatFeedEntry.threat_type == record.threat_type,
        )
        .first()
    )
    if existing:
        return

    entry = ThreatFeedEntry(
        domain=record.domain,
        source=record.source,
        threat_type=record.threat_type,
        confidence=record.confidence,
        first_seen_at=datetime.utcnow(),
    )
    db.add(entry)

    # Bump domain reputation
    repo = db.query(DomainReputation).filter(DomainReputation.domain == record.domain).first()
    if not repo:
        repo = DomainReputation(
            domain=record.domain,
            risk_score=0.0,
            domain_age_days=None,
            registrar=None,
            whois_privacy_enabled=None,
            flags={},
        )
        db.add(repo)
        db.flush()
    flags = dict(repo.flags or {})
    flags["in_threat_feed"] = True
    repo.flags = flags
    repo.risk_score = max(repo.risk_score, min(1.0, 0.6 + record.confidence * 0.4))
    repo.last_seen_at = datetime.utcnow()
    db.add(repo)


def _create_impersonation_alerts_for_domain(db: Session, suspicious_domain: str) -> None:
    # For each watched brand/domain, see if this domain looks like an impersonator.
    watches = db.query(TenantDomainWatch).all()
    if not watches:
        return

    suspicious_homograph = detect_homograph(suspicious_domain)
    for watch in watches:
        typosquats = detect_typosquatting(suspicious_domain, [watch.domain])
        if typosquats:
            _, score = typosquats[0]
            alert = DomainImpersonationAlert(
                tenant_id=watch.tenant_id,
                brand_name=watch.brand_name,
                suspicious_domain=suspicious_domain,
                detection_type="typosquat",
                risk_score=float(score),
                status=AlertStatus.open,
            )
            db.add(alert)
        elif suspicious_homograph:
            alert = DomainImpersonationAlert(
                tenant_id=watch.tenant_id,
                brand_name=watch.brand_name,
                suspicious_domain=suspicious_domain,
                detection_type="homograph",
                risk_score=0.9,
                status=AlertStatus.open,
            )
            db.add(alert)


def ingest_feeds(db: Session, sources: List[ThreatFeedSource]) -> None:
    for source in sources:
        for record in source.fetch():
            upsert_threat_entry(db, record)
            _create_impersonation_alerts_for_domain(db, suspicious_domain=record.domain)
    db.commit()


def main() -> None:  # pragma: no cover - manual execution entrypoint
    init_db()
    db = SessionLocal()
    try:
        sources: List[ThreatFeedSource] = []  # populate with real sources
        ingest_feeds(db, sources)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    main()

