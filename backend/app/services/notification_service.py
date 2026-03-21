from __future__ import annotations

import logging
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import httpx # Already in requirements.txt (line 9)

from ..db_models import (
    SecurityAlert,
    NotificationChannel,
    NotificationChannelType,
    Tenant,
)
from ..observability import ALERTS_SENT_TOTAL, ALERTS_FAILED_TOTAL

logger = logging.getLogger(__name__)


async def dispatch_security_alert_notifications(db: Session, alert_id: int) -> None:
    """
    Dispatches notifications for a single security alert to all configured channels for the tenant.
    """
    alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
    if not alert:
        logger.warning(f"Alert ID {alert_id} not found during notification dispatch.")
        return

    channels = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.tenant_id == alert.tenant_id,
            NotificationChannel.is_active == True,
        )
        .all()
    )

    if not channels:
        logger.info(f"No active notification channels for Tenant {alert.tenant_id}.")
        return

    logger.debug(f"Dispatching Alert ID {alert_id} to {len(channels)} channels.")

    for channel in channels:
        try:
            if channel.type == NotificationChannelType.slack:
                await _send_to_slack(channel.config, alert)
            elif channel.type == NotificationChannelType.webhook:
                await _send_to_webhook(channel.config, alert)
            elif channel.type == NotificationChannelType.email:
                await _send_email(channel.config, alert)
            
            ALERTS_SENT_TOTAL.labels(type=channel.type).inc()
        except Exception as exc:
            ALERTS_FAILED_TOTAL.labels(type=channel.type).inc()
            logger.error(
                f"Failed to dispatch notification to {channel.type} for alert {alert_id}: {exc}",
                extra={
                    "event": "notification_dispatch_failed",
                    "channel_id": channel.id,
                    "alert_id": alert_id,
                    "tenant_id": alert.tenant_id,
                    "error": str(exc),
                },
            )


async def _send_to_slack(config: Dict[str, Any], alert: SecurityAlert) -> None:
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Missing webhook_url in Slack channel configuration")

    message = {
        "text": f"🚨 *Security Alert: {alert.alert_type}*",
        "attachments": [
            {
                "color": "danger" if alert.severity in ["critical", "high"] else "warning",
                "fields": [
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                    {"title": "Type", "value": alert.alert_type, "short": True},
                    {"title": "URL", "value": alert.url or "N/A", "short": False},
                    {"title": "Domain", "value": alert.domain or "N/A", "short": True},
                    {"title": "Time", "value": alert.created_at.isoformat(), "short": True},
                ],
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=message)
        response.raise_for_status()


async def _send_to_webhook(config: Dict[str, Any], alert: SecurityAlert) -> None:
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Missing webhook_url in Webhook channel configuration")

    payload = {
        "event": "security_alert",
        "alert_id": alert.id,
        "tenant_id": alert.tenant_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "url": alert.url,
        "domain": alert.domain,
        "created_at": alert.created_at.isoformat(),
        "status": alert.status,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()


async def _send_email(config: Dict[str, Any], alert: SecurityAlert) -> None:
    to_email = config.get("email")
    if not to_email:
        raise ValueError("Missing 'email' in Email channel configuration")

    # In a real system, use an SMTP client or AWS SES. 
    # For now, we mock/log the email dispatch.
    subject = f"Argus Alert: [{alert.severity.upper()}] {alert.alert_type}"
    body = (
        f"A new security alert was generated for your tenant.\n\n"
        f"Level: {alert.severity.upper()}\n"
        f"Type: {alert.alert_type}\n"
        f"URL: {alert.url or 'N/A'}\n"
        f"Domain: {alert.domain or 'N/A'}\n"
        f"Time: {alert.created_at.isoformat()}\n\n"
        f"View details in your Argus dashboard."
    )
    
    logger.info(f"MOCK EMAIL SENT to {to_email}: {subject}")
    # In practice: await aiosmtplib.send(...)
