from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from ..db_models import Scan, ScanResult, ScanMetadata, EmailScan, Tenant
from ..schemas import PredictRequest
from ..model import EnsembleModel, model_instance
from .alert_service import create_security_alert
from ..db_models import SecurityAlertType, AlertSeverity

logger = logging.getLogger(__name__)

class GmailService:
    @staticmethod
    async def fetch_and_scan_emails(
        db: Session,
        tenant_id: int,
        user_id: int,
        gmail_api_client: Any # Placeholder for Google API client
    ) -> List[EmailScan]:
        """
        Fetch recent emails from Gmail API, extract links, and scan them.
        """
        # 1. Fetch messages (Implementation with real API)
        # results = gmail_api_client.users().messages().list(userId='me', q='is:unread', maxResults=10).execute()
        # messages = results.get('messages', [])
        
        # Mocking for demonstration
        mock_emails = [
            {
                "id": "msg_123",
                "subject": "System Alert: Security Breach",
                "sender": "sec-alert@google-security.net",
                "body": "Your account has been compromised. Please login here to reset your password: http://account-secure-login.bit.ly/update",
                "links": ["http://account-secure-login.bit.ly/update"]
            },
            {
                "id": "msg_456",
                "subject": "Lunch Today?",
                "sender": "friend@gmail.com",
                "body": "Hey, let me know if you want to grab lunch at https://www.yelp.com/biz/good-food",
                "links": ["https://www.yelp.com/biz/good-food"]
            }
        ]

        email_scans = []
        for email_data in mock_emails:
            # Check if already scanned
            existing = db.query(EmailScan).filter(EmailScan.email_id == email_data["id"]).first()
            if existing:
                continue

            # Process each link (simplified to first link for now)
            url = email_data["links"][0] if email_scans else "no-link-found" # Simplified
            if not email_data["links"]:
                continue

            url = email_data["links"][0]
            
            # 2. Call Detector API (internal call)
            # Use model_instance directly
            try:
                # In real scenario, we might want to scan concurrent links
                result = await model_instance.predict(url, html=None, screenshot=None, db=db)
                
                # 3. Persist Scan
                scan = Scan(
                    tenant_id=tenant_id,
                    url=url,
                    source="gmail",
                    created_by_user_id=user_id,
                )
                db.add(scan)
                db.flush()

                scan_result = ScanResult(
                    scan_id=scan.id,
                    prediction=result.prediction,
                    confidence=result.confidence,
                    explanation=result.explanation.model_dump(),
                )
                db.add(scan_result)

                # 4. Store Email Scan Result
                email_scan = EmailScan(
                    tenant_id=tenant_id,
                    email_id=email_data["id"],
                    subject=email_data["subject"],
                    sender=email_data["sender"],
                    scan_id=scan.id,
                    detection_result=result.prediction,
                    risk_score=result.confidence,
                )
                db.add(email_scan)
                email_scans.append(email_scan)

                # 5. Create Alert if Phishing
                if result.prediction == "phishing" and result.confidence > 0.85:
                    create_security_alert(
                        db=db,
                        tenant_id=tenant_id,
                        alert_type=SecurityAlertType.PHISHING_DETECTED,
                        severity=AlertSeverity.critical if result.confidence > 0.95 else AlertSeverity.high,
                        url=url,
                        scan_id=scan.id,
                    )
                
                db.commit()
            except Exception as exc:
                logger.error(f"Failed to scan email {email_data['id']}: {exc}")
                db.rollback()

        return email_scans
