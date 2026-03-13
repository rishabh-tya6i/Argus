"""
Notification Service for Tenant Alerts.
"""
from typing import List
import logging
import json

from sqlalchemy.orm import Session
from backend.app.db_models import DomainImpersonationAlert, Tenant

logger = logging.getLogger(__name__)

def dispatch_impersonation_alerts(db: Session, alerts: List[DomainImpersonationAlert]) -> None:
    """
    Dispatches notifications (Webhook/Slack/Email) for high-confidence alerts based on Tenant configurations.
    """
    if not alerts:
        return

    # Group alerts by tenant to minimize DB lookups
    tenant_ids = list(set(a.tenant_id for a in alerts))
    tenants = {t.id: t for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()}

    for alert in alerts:
        tenant = tenants.get(alert.tenant_id)
        if not tenant:
            continue

        config = tenant.config or {}
        notifications = config.get("notifications", {})
        
        # Only notify on high confidence
        if alert.risk_score < 0.6:
            continue

        msg = f"🚨 [Threat Intel] New impersonation domain detected for '{alert.brand_name}': {alert.suspicious_domain} (Risk: {alert.risk_score:.2f}, Type: {alert.detection_type})"

        if notifications.get("slack_webhook"):
            _send_slack(notifications["slack_webhook"], msg)
        
        if notifications.get("email"):
            _send_email(notifications["email"], "New Threat Intelligence Alert", msg)


def _send_slack(webhook_url: str, message: str) -> None:
    """Mock sending to slack"""
    logger.info(f"Slack Notification -> {webhook_url}: {message}")


def _send_email(to_email: str, subject: str, body: str) -> None:
    """Mock sending an email"""
    logger.info(f"Email Notification -> {to_email} | {subject}\n{body}")
