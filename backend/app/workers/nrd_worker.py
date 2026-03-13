"""
Newly Registered Domain (NRD) feed ingestion worker.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from sqlalchemy.orm import Session

from backend.app.db import SessionLocal, init_db
from backend.app.db_models import TenantDomainWatch
from backend.app.services.domain_intel import detect_typosquatting, detect_homograph, normalize_domain
from backend.app.workers.threat_feed_worker import process_threat_alert

logger = logging.getLogger(__name__)


@dataclass
class NRDRecord:
    domain: str
    date_registered: str
    registrar: str | None = None


class NRDFeedSource:
    """Abstract interface for NRD feed sources."""

    def fetch(self) -> Iterable[NRDRecord]:  # pragma: no cover
        raise NotImplementedError


class MockNRDFeedSource(NRDFeedSource):
    """A mock NRD source for testing."""
    def fetch(self) -> Iterable[NRDRecord]:
        return [
            NRDRecord(domain="paypal-login-update.com", date_registered="2026-03-14"),
            NRDRecord(domain="xn--microsft-c3a.com", date_registered="2026-03-14"), # homograph of microsoft
            NRDRecord(domain="amaz0n-support.net", date_registered="2026-03-14"),
        ]


def process_nrd_record(db: Session, record: NRDRecord) -> None:
    watches = db.query(TenantDomainWatch).all()
    if not watches:
        return

    suspicious_domain = normalize_domain(record.domain)
    suspicious_homograph = detect_homograph(suspicious_domain)

    for watch in watches:
        typosquats = detect_typosquatting(suspicious_domain, [watch.domain])
        if typosquats:
            _, score = typosquats[0]
            process_threat_alert(db, watch, suspicious_domain, "typosquat_nrd", float(score))
        elif suspicious_homograph:
            process_threat_alert(db, watch, suspicious_domain, "homograph_nrd", 0.9)


def ingest_nrd_feeds(db: Session, sources: List[NRDFeedSource]) -> None:
    for source in sources:
        for record in source.fetch():
            process_nrd_record(db, record)


def main() -> None:  # pragma: no cover
    init_db()
    db = SessionLocal()
    try:
        sources: List[NRDFeedSource] = [MockNRDFeedSource()]
        ingest_nrd_feeds(db, sources)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    main()
