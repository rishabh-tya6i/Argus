"""
Scan automation service helper
"""

import logging
from sqlalchemy.orm import Session

import logging
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.db_models import Scan, ScanResult, SandboxRun, SandboxStatus

logger = logging.getLogger(__name__)

def trigger_auto_scan(db: Session, tenant_id: int, url: str) -> bool:
    """
    Triggers an automatic sandbox/security scan for a suspicious URL.
    """
    try:
        scan = Scan(
            tenant_id=tenant_id,
            url=url,
            source="threat_intel_auto",
            created_at=datetime.utcnow()
        )
        db.add(scan)
        db.flush()

        # Create Sandbox run to represent automated queuing
        sandbox = SandboxRun(
            tenant_id=tenant_id,
            scan_id=scan.id,
            url=url,
            status=SandboxStatus.queued
        )
        db.add(sandbox)
        db.commit()
        db.refresh(scan)
        db.refresh(sandbox)
        
        logger.info(f"[AutoScan] Queued scan ID {scan.id} (Sandbox {sandbox.id}) for auto-discovered URL: {url}")
        return True
    except Exception as e:
        logger.error(f"Failed to auto-scan {url}: {e}")
        return False
