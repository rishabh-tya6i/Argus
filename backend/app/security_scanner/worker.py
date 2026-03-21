from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set

import logging
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

from ..db_models import (
    SecurityScanRun,
    SecurityScanIssue,
    SecurityScanArtifact,
    SecurityScanStatus,
    SecurityIssueSeverity,
    ScanResult
)
from ..services.domain_intel import evaluate_domain_for_url
from ..schemas import ExplanationReason

try:
    from playwright.async_api import async_playwright  # type: ignore
except Exception:  # pragma: no cover
    async_playwright = None

SECURITY_SCAN_TIMEOUT_SECONDS = int(os.getenv("SECURITY_SCAN_TIMEOUT_SECONDS", "30"))
SECURITY_SCAN_STORAGE_ROOT = os.getenv("SECURITY_SCAN_STORAGE_ROOT", "security_artifacts")


@dataclass
class ScanSignals:
    suspicious_js_execution: bool = False
    external_credential_endpoints: Set[str] = None
    suspicious_domains: Set[str] = None
    ip_based_hosts: Set[str] = None
    missing_csp: bool = False
    missing_hsts: bool = False
    missing_x_frame_options: bool = False
    missing_referrer_policy: bool = False
    http_downgrade: bool = False
    excessive_redirects: bool = False

    def __post_init__(self):
        self.external_credential_endpoints = set()
        self.suspicious_domains = set()
        self.ip_based_hosts = set()


async def _run_playwright(db: Session, run: SecurityScanRun, storage_dir: Path) -> Tuple[List[SecurityScanIssue], List[SecurityScanArtifact], ScanSignals]:
    if async_playwright is None:
        return [], [], ScanSignals()

    issues: List[SecurityScanIssue] = []
    artifacts: List[SecurityScanArtifact] = []
    signals = ScanSignals()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        js_hook = """
        (() => {
          const log = (...args) => console.log("__SCAN_JS_EVENT__", ...args);
          const origEval = window.eval;
          window.eval = function(...args) { log("eval"); return origEval.apply(this, args); };
          const origAtob = window.atob;
          window.atob = function(...args) { log("atob"); return origAtob.apply(this, args); };
        })();
        """
        await context.add_init_script(js_hook)

        # 1. Network Request Analysis
        def handle_request(request):
            url = request.url
            if re.match(r'^https?://[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', url):
                signals.ip_based_hosts.add(url)

            if request.method in ["POST", "PUT"] and ("login" in url.lower() or "auth" in url.lower() or "submit" in url.lower()):
                # Exclude internal 
                pass # Check in details later based on base url

        page.on("request", handle_request)

        # 2. Security Headers
        async def handle_response(response):
            if response.url == run.url:
                headers = response.headers
                
                # Check for redirects
                if response.status in [301, 302, 307, 308]:
                    location = headers.get("location", "")
                    if run.url.startswith("https") and location.startswith("http://"):
                        signals.http_downgrade = True

                # Check security headers on the final response
                if response.status == 200:
                    x_frame_options = headers.get("x-frame-options", "").upper()
                    if x_frame_options not in ["DENY", "SAMEORIGIN"]:
                        signals.missing_x_frame_options = True
                    
                    if "strict-transport-security" not in headers:
                        signals.missing_hsts = True
                    
                    if "content-security-policy" not in headers:
                        signals.missing_csp = True
                    
                    if "referrer-policy" not in headers:
                        signals.missing_referrer_policy = True

        page.on("response", lambda resp: asyncio.ensure_future(handle_response(resp)))

        async def handle_console(msg):
            if msg.text().startswith("__SCAN_JS_EVENT__"):
                signals.suspicious_js_execution = True

        page.on("console", lambda msg: asyncio.ensure_future(handle_console(msg)))

        try:
            response = await page.goto(run.url, wait_until="networkidle", timeout=SECURITY_SCAN_TIMEOUT_SECONDS * 1000)
            
            # Check redirect chain length
            chain = response.request.redirect_chain if response else []
            if len(chain) > 3:
                signals.excessive_redirects = True

            # External Credential endpoint check.
            forms = await page.locator("form").all()
            base_domain = run.url.split("/")[2] if "//" in run.url else run.url.split("/")[0]

            for form in forms:
                action = await form.get_attribute("action")
                has_password = await form.locator('input[type="password"]').count() > 0
                if action and has_password:
                    action_domain = action.split("/")[2] if "//" in action else ""
                    if action_domain and action_domain != base_domain:
                         signals.external_credential_endpoints.add(action)

        except Exception as e:
            pass

        # Capture final screenshot
        storage_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = storage_dir / "final.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            artifacts.append(
                SecurityScanArtifact(
                    run_id=run.id,
                    artifact_type="screenshot",
                    storage_path=str(screenshot_path),
                    created_at=datetime.utcnow()
                )
            )
        except Exception:
            pass
        
        # DOM Analysis
        try:
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for hidden credential inputs
            hidden_creds = soup.find_all("input", type="hidden", attrs={"name": re.compile(r'user|pass|auth|login', re.I)})
            if hidden_creds:
                 issues.append(SecurityScanIssue(
                     run_id=run.id,
                     severity=SecurityIssueSeverity.HIGH,
                     category="Forms",
                     description="Found hidden credential inputs in the DOM.",
                     remediation="Remove hidden inputs used for authentication as they can expose sensitive data or be manipulated."
                 ))

        except Exception:
            pass

        await browser.close()

    # Generate Issues from signals
    if signals.suspicious_js_execution:
        issues.append(SecurityScanIssue(
            run_id=run.id,
            severity=SecurityIssueSeverity.HIGH,
            category="Scripts",
            description="Suspicious JavaScript execution detected (e.g., eval or atob parsing dynamically).",
            remediation="Refactor code to avoid dynamic evaluation of scripts and ensure scripts are served from trusted locations."
        ))

    if signals.external_credential_endpoints:
        issues.append(SecurityScanIssue(
            run_id=run.id,
            severity=SecurityIssueSeverity.CRITICAL,
            category="Forms",
            description=f"Form posting credentials to external domain: {', '.join(signals.external_credential_endpoints)}",
            remediation="Ensure credential submission endpoints match the origin domain to prevent data exfiltration."
        ))

    if signals.ip_based_hosts:
        issues.append(SecurityScanIssue(
            run_id=run.id,
            severity=SecurityIssueSeverity.MEDIUM,
            category="Network",
            description=f"Found resources requested from raw IP addresses: {', '.join(signals.ip_based_hosts)}",
            remediation="Use domain names instead of raw IP addresses for reliable routing and HTTPS validation."
        ))

    if signals.missing_csp:
        issues.append(SecurityScanIssue(
            run_id=run.id, severity=SecurityIssueSeverity.HIGH, category="Headers",
            description="Missing Content-Security-Policy header.", remediation="Implement a strict CSP to restrict script and resource loading."
        ))
    if signals.missing_hsts:
        issues.append(SecurityScanIssue(
            run_id=run.id, severity=SecurityIssueSeverity.MEDIUM, category="Headers",
            description="Missing Strict-Transport-Security header.", remediation="Enable HSTS to enforce secure connections."
        ))
    if signals.missing_x_frame_options:
        issues.append(SecurityScanIssue(
            run_id=run.id, severity=SecurityIssueSeverity.MEDIUM, category="Headers",
            description="Missing or weak X-Frame-Options header.", remediation="Set X-Frame-Options to DENY or SAMEORIGIN to prevent clickjacking."
        ))
    
    if signals.http_downgrade:
        issues.append(SecurityScanIssue(
            run_id=run.id, severity=SecurityIssueSeverity.CRITICAL, category="TLS",
            description="HTTP downgrade redirect detected.", remediation="Ensure all redirects maintain or upgrade to HTTPS."
        ))

    if signals.excessive_redirects:
        issues.append(SecurityScanIssue(
            run_id=run.id, severity=SecurityIssueSeverity.LOW, category="Redirects",
            description="Excessive redirect chains.", remediation="Minimize redirects to reduce attack surface and improve performance."
        ))

    return issues, artifacts, signals


async def execute_security_scan(db: Session, run: SecurityScanRun) -> None:
    run.status = SecurityScanStatus.running
    run.started_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)

    storage_dir = Path(SECURITY_SCAN_STORAGE_ROOT) / str(run.id)

    try:
        issues, artifacts, signals = await _run_playwright(db, run, storage_dir)

        # Domain intel & model explanation signals
        try:
            _domain, domain_risk, _reasons = evaluate_domain_for_url(db, run.url)
            if domain_risk > 0.5:
                issues.append(SecurityScanIssue(
                    run_id=run.id, severity=SecurityIssueSeverity.HIGH, category="Network",
                    description=f"High domain risk score: {domain_risk}",
                    remediation="Investigate root cause of domain blacklisting or suspicious registrar configurations."
                ))
        except Exception:
            pass

        # Calculate score (start from 100, deduct based on severity)
        score = 100
        for issue in issues:
            if issue.severity == SecurityIssueSeverity.CRITICAL:
                score -= 20
            elif issue.severity == SecurityIssueSeverity.HIGH:
                score -= 15
            elif issue.severity == SecurityIssueSeverity.MEDIUM:
                score -= 10
            elif issue.severity == SecurityIssueSeverity.LOW:
                score -= 5
        
        run.score = max(0, min(100, score))
        run.summary = f"Scan complete. Found {len(issues)} issues."
        run.finished_at = datetime.utcnow()
        run.status = SecurityScanStatus.completed

        for issue in issues:
            db.add(issue)
        for art in artifacts:
            db.add(art)

        db.add(run)
        db.commit()

    except Exception as e:
        run.status = SecurityScanStatus.failed
        run.finished_at = datetime.utcnow()
        run.summary = f"Security Scan failed: {e}"
        db.add(run)
        db.commit()


async def worker_loop() -> None:
    from ..db import SessionLocal, init_db
    from .queue import dequeue_security_scan
    from ..db_models import SecurityScanRun, SecurityScanStatus
    from ..observability import update_worker_heartbeat, set_correlation_ctx, setup_logging

    setup_logging()
    init_db()
    _WORKER = "security_scanner"
    logger.info(f"Starting { _WORKER} worker loop")
    set_correlation_ctx(worker_name=_WORKER)
    db = SessionLocal()
    try:
        while True:
            update_worker_heartbeat(_WORKER)

            # Prefer Redis queue
            run_id = dequeue_security_scan(block=True, timeout=10)
            if run_id is not None:
                run = db.query(SecurityScanRun).filter(SecurityScanRun.id == run_id).first()
                if run:
                    set_correlation_ctx(worker_name=_WORKER, scan_id=f"security_{run.id}")
                    await execute_security_scan(db, run)
                continue

            # Fallback: poll DB
            run = db.query(SecurityScanRun).filter(SecurityScanRun.status == SecurityScanStatus.queued).first()
            if run:
                await execute_security_scan(db, run)
                continue

            await asyncio.sleep(5)
    finally:
        db.close()


def main() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
