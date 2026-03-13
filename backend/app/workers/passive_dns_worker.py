"""
Passive DNS monitoring worker.
Track DNS changes and identify domains suddenly resolving to suspicious hosting providers.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from backend.app.db import SessionLocal, init_db
from backend.app.db_models import DomainImpersonationAlert, AlertStatus, TenantDomainWatch

logger = logging.getLogger(__name__)


# A mock list of suspicious ASNs or IP ranges
SUSPICIOUS_IPS = {
    "192.168.1.100", # Example mock bad IP
    "10.0.0.99"
}

def resolve_domain(domain: str) -> List[str]:
    """Mock DNS resolver. In reality, use pdns feeds or aiodns."""
    # We will simulate resolve for testing.
    # We map some known test domains to suspicious IPs.
    if "update" in domain or "secure" in domain:
        return ["192.168.1.100"]
    try:
        return [socket.gethostbyname(domain)]
    except Exception:
        return []

def process_pdns_for_alerts(db: Session) -> None:
    """
    Check currently open alerts and try to resolve them.
    If they resolve to a known suspicious infrastructure, bump the risk score.
    """
    alerts = db.query(DomainImpersonationAlert).filter(DomainImpersonationAlert.status == AlertStatus.open).all()
    if not alerts:
        return
        
    for alert in alerts:
        ips = resolve_domain(alert.suspicious_domain)
        if ips:
            enrichment = alert.enrichment or {}
            enrichment["ip_address"] = ips[0]
            alert.enrichment = enrichment

            for ip in ips:
                if ip in SUSPICIOUS_IPS:
                    # Found on suspicious infra, bump risk and create a new notification/log if needed.
                    if alert.risk_score < 0.95:
                        alert.risk_score = min(1.0, alert.risk_score + 0.2)
                        alert.detection_type += "+suspicious_infra"
                        logger.info(f"Bumped risk for {alert.suspicious_domain} due to passive DNS resolution {ip}")
                    break
        db.add(alert)
    
    db.commit()


def main() -> None:  # pragma: no cover
    init_db()
    db = SessionLocal()
    try:
        process_pdns_for_alerts(db)
    finally:
        db.close()

if __name__ == "__main__":  # pragma: no cover
    main()
