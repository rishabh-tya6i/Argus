"""
Certificate Transparency (CT) Log monitoring worker.
"""

from __future__ import annotations

import logging
import traceback
import certstream

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

_WORKER = "ct_log"


def process_ct_cert(message: dict, context) -> None:
    """Callback function for handling certstream messages."""
    if message['message_type'] != "certificate_update":
        return

    # Update heartbeat so alert rules know this worker is alive
    update_worker_heartbeat(_WORKER)

    all_domains = message['data']['leaf_cert']['all_domains']

    db = SessionLocal()
    try:
        watches = db.query(TenantDomainWatch).all()
        if not watches:
            return

        for raw_domain in all_domains:
            suspicious_domain = normalize_domain(raw_domain)
            suspicious_homograph = detect_homograph(suspicious_domain)

            set_correlation_ctx(
                worker_name=_WORKER,
                url_domain=suspicious_domain,
            )

            for watch in watches:
                typosquats = detect_typosquatting(suspicious_domain, [watch.domain])
                if typosquats:
                    _, score = typosquats[0]
                    # Filter out exact matches (the real brand registering a sub/cert)
                    if suspicious_domain == watch.domain or suspicious_domain.endswith("." + watch.domain):
                        continue
                    with tracer.start_as_current_span("ct_log.process_cert") as span:
                        span.set_attribute("suspicious_domain", suspicious_domain)
                        span.set_attribute("detection_type", "typosquat_ct")
                        set_correlation_ctx(detection_type="typosquat_ct")
                        process_threat_alert(db, watch, suspicious_domain, "typosquat_ct", float(score))
                        THREAT_INTEL_ALERTS_TOTAL.labels(detection_type="typosquat_ct").inc()
                        logger.info(
                            "CT log threat alert generated",
                            extra={**get_correlation_ctx(), "event": "ct_alert_generated", "score": score},
                        )
                elif suspicious_homograph:
                    with tracer.start_as_current_span("ct_log.process_cert") as span:
                        span.set_attribute("suspicious_domain", suspicious_domain)
                        span.set_attribute("detection_type", "homograph_ct")
                        set_correlation_ctx(detection_type="homograph_ct")
                        process_threat_alert(db, watch, suspicious_domain, "homograph_ct", 0.9)
                        THREAT_INTEL_ALERTS_TOTAL.labels(detection_type="homograph_ct").inc()
                        logger.info(
                            "CT log homograph alert generated",
                            extra={**get_correlation_ctx(), "event": "ct_alert_generated"},
                        )

            QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="success").inc()

    except Exception as exc:
        QUEUE_JOBS_TOTAL.labels(worker=_WORKER, status="failed").inc()
        WORKER_FAILURES_TOTAL.labels(worker=_WORKER).inc()
        logger.error(
            "CT log worker processing error",
            extra={
                **get_correlation_ctx(),
                "event": "worker_processing_error",
                "worker_name": _WORKER,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
    finally:
        db.close()


def main(run_forever: bool = True) -> None:  # pragma: no cover
    init_db()
    set_correlation_ctx(worker_name=_WORKER)
    if run_forever:
        logger.info("[*] Starting CertStream CT Log Listener...")
        # Blocks indefinitely
        certstream.listen_for_events(process_ct_cert, url='wss://certstream.calidog.io/')
    else:
        logger.info("[*] Running simulated CT Log processing for --intel dev test...")
        mock_msg = {
            "message_type": "certificate_update",
            "data": {
                "leaf_cert": {
                    "all_domains": ["secure-login-apple.com", "xn--exmple-dua.com"]
                }
            }
        }
        process_ct_cert(mock_msg, None)


if __name__ == "__main__":  # pragma: no cover
    main()
