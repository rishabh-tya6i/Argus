"""
Certificate Transparency (CT) Log monitoring worker.
"""

from __future__ import annotations

import logging
import certstream

from backend.app.db import SessionLocal, init_db
from backend.app.db_models import TenantDomainWatch
from backend.app.services.domain_intel import detect_typosquatting, detect_homograph, normalize_domain
from backend.app.workers.threat_feed_worker import process_threat_alert

logger = logging.getLogger(__name__)


def process_ct_cert(message: dict, context) -> None:
    """Callback function for handling certstream messages."""
    if message['message_type'] != "certificate_update":
        return

    all_domains = message['data']['leaf_cert']['all_domains']
    
    db = SessionLocal()
    try:
        watches = db.query(TenantDomainWatch).all()
        if not watches:
            return

        for raw_domain in all_domains:
            suspicious_domain = normalize_domain(raw_domain)
            suspicious_homograph = detect_homograph(suspicious_domain)

            for watch in watches:
                typosquats = detect_typosquatting(suspicious_domain, [watch.domain])
                if typosquats:
                    _, score = typosquats[0]
                    # Filter out exact matches (the real brand registering a sub/cert)
                    if suspicious_domain == watch.domain or suspicious_domain.endswith("." + watch.domain):
                        continue
                    process_threat_alert(db, watch, suspicious_domain, "typosquat_ct", float(score))
                elif suspicious_homograph:
                    process_threat_alert(db, watch, suspicious_domain, "homograph_ct", 0.9)
    finally:
        db.close()


def main(run_forever: bool = True) -> None:  # pragma: no cover
    init_db()
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
