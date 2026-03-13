"""
Newly Registered Domain (NRD) feed ingestion worker.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Iterable, List

from sqlalchemy.orm import Session

from backend.app.db import SessionLocal, init_db
from backend.app.db_models import TenantDomainWatch
from backend.app.services.domain_intel import detect_typosquatting, detect_homograph, normalize_domain
from backend.app.workers.threat_feed_worker import process_threat_alert
from backend.app.observability import (
    tracer,
    set_correlation_ctx,
    get_correlation_ctx,
    update_worker_heartbeat,
    THREAT_INTEL_ALERTS_TOTAL,
    WORKER_FAILURES_TOTAL,
    QUEUE_JOBS_TOTAL,
)

logger = logging.getLogger(__name__)

_WORKER = "nrd"


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
            NRDRecord(domain="xn--microsft-c3a.com", date_registered="2026-03-14"),  # homograph of microsoft
            NRDRecord(domain="amaz0n-support.net", date_registered="2026-03-14"),
        ]


def process_nrd_record(db: Session, record: NRDRecord) -> None:
    watches = db.query(TenantDomainWatch).all()
    if not watches:
        return

    suspicious_domain = normalize_domain(record.domain)
    suspicious_homograph = detect_homograph(suspicious_domain)

    set_correlation_ctx(worker_name=_WORKER, url_domain=suspicious_domain)

    for watch in watches:
        typosquats = detect_typosquatting(suspicious_domain, [watch.domain])
        if typosquats:
            _, score = typosquats[0]
            with tracer.start_as_current_span("nrd.process_record") as span:
                span.set_attribute("suspicious_domain", suspicious_domain)
                span.set_attribute("detection_type", "typosquat_nrd")
                set_correlation_ctx(detection_type="typosquat_nrd")
                process_threat_alert(db, watch, suspicious_domain, "typosquat_nrd", float(score))
                THREAT_INTEL_ALERTS_TOTAL.labels(detection_type="typosquat_nrd").inc()
                logger.info(
                    "NRD typosquat alert generated",
                    extra={**get_correlation_ctx(), "event": "nrd_alert_generated", "score": score},
                )
        elif suspicious_homograph:
            with tracer.start_as_current_span("nrd.process_record") as span:
                span.set_attribute("suspicious_domain", suspicious_domain)
                span.set_attribute("detection_type", "homograph_nrd")
                set_correlation_ctx(detection_type="homograph_nrd")
                process_threat_alert(db, watch, suspicious_domain, "homograph_nrd", 0.9)
                THREAT_INTEL_ALERTS_TOTAL.labels(detection_type="homograph_nrd").inc()
                logger.info(
                    "NRD homograph alert generated",
                    extra={**get_correlation_ctx(), "event": "nrd_alert_generated"},
                )


def ingest_nrd_feeds(db: Session, sources: List[NRDFeedSource]) -> None:
    for source in sources:
        update_worker_heartbeat(_WORKER)
        for record in source.fetch():
            try:
                process_nrd_record(db, record)
                QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="success").inc()
            except Exception as exc:
                QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="failed").inc()
                WORKER_FAILURES_TOTAL.labels(worker=_WORKER).inc()
                logger.error(
                    "NRD record processing error",
                    extra={
                        **get_correlation_ctx(),
                        "event": "worker_processing_error",
                        "worker_name": _WORKER,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )


def main() -> None:  # pragma: no cover
    init_db()
    set_correlation_ctx(worker_name=_WORKER)
    db = SessionLocal()
    try:
        sources: List[NRDFeedSource] = [MockNRDFeedSource()]
        ingest_nrd_feeds(db, sources)
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    main()
