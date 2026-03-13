from __future__ import annotations

"""
Sandbox runner for dynamic analysis of suspicious URLs.

This module is designed to be used by the sandbox worker to execute each
SandboxRun inside an isolated headless Chromium instance (via Playwright),
capture key events (network, redirects, JS signals), and persist artifacts
such as screenshots and DOM snapshots.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from ..db_models import SandboxRun, SandboxEvent, SandboxArtifact, SandboxStatus, ScanResult
from ..services.domain_intel import evaluate_domain_for_url
from ..schemas import ExplanationReason

try:
    from playwright.async_api import async_playwright  # type: ignore
except Exception:  # pragma: no cover - Playwright not installed in all environments
    async_playwright = None


SANDBOX_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "30"))
SANDBOX_STORAGE_ROOT = os.getenv("SANDBOX_STORAGE_ROOT", "sandbox_artifacts")


@dataclass
class SandboxSignals:
    credential_exfiltration: bool = False
    redirect_to_malicious: bool = False
    suspicious_js_execution: bool = False
    hidden_login_form: bool = False


async def _run_playwright(db: Session, run: SandboxRun, storage_dir: Path) -> Tuple[float, str, List[SandboxEvent], List[SandboxArtifact], SandboxSignals]:
    """
    Execute the sandboxed browser session and collect events/artifacts.
    Returns (risk_score, summary, events, artifacts, signals).
    """
    if async_playwright is None:
        # Playwright not available; mark as failed with no dynamic signal.
        return 0.0, "Playwright not installed; sandbox skipped.", [], [], SandboxSignals()

    events: List[SandboxEvent] = []
    artifacts: List[SandboxArtifact] = []
    signals = SandboxSignals()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context()

        page = await context.new_page()

        # Inject lightweight JS hooks to capture eval/atob usage.
        js_hook = """
        (() => {
          const log = (...args) => console.log("__SANDBOX_JS_EVENT__", ...args);
          const origEval = window.eval;
          window.eval = function(...args) { log("eval"); return origEval.apply(this, args); };
          const origAtob = window.atob;
          window.atob = function(...args) { log("atob"); return origAtob.apply(this, args); };
        })();
        """
        await context.add_init_script(js_hook)

        def log_event(event_type: str, data: Dict):
            events.append(
                SandboxEvent(
                    sandbox_run_id=run.id,
                    event_type=event_type,
                    data=data,
                    timestamp=datetime.utcnow(),
                )
            )

        page.on(
            "request",
            lambda request: log_event(
                "network_request",
                {
                    "url": request.url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                },
            ),
        )

        async def on_response(response):
            log_event(
                "network_response",
                {
                    "url": response.url,
                    "status": response.status,
                },
            )

        page.on("response", lambda resp: asyncio.ensure_future(on_response(resp)))

        async def on_console(msg):
            text = msg.text()
            if text.startswith("__SANDBOX_JS_EVENT__"):
                # Mark suspicious JS execution
                signals.suspicious_js_execution = True
                log_event(
                    "script_execution",
                    {"signal": text.replace("__SANDBOX_JS_EVENT__", "").strip()},
                )

        page.on("console", lambda msg: asyncio.ensure_future(on_console(msg)))

        # Navigate and wait for network to settle or timeout.
        try:
            await page.goto(run.url, wait_until="networkidle", timeout=SANDBOX_TIMEOUT_SECONDS * 1000)
        except Exception as e:
            log_event("navigation_error", {"error": str(e)})

        # Capture final screenshot
        storage_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = storage_dir / "final.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            artifacts.append(
                SandboxArtifact(
                    sandbox_run_id=run.id,
                    artifact_type="screenshot",
                    storage_path=str(screenshot_path),
                    created_at=datetime.utcnow(),
                )
            )
        except Exception as e:  # pragma: no cover
            log_event("screenshot_error", {"error": str(e)})

        # Capture DOM snapshot for later offline analysis
        try:
            html = await page.content()
            dom_path = storage_dir / "dom.html"
            with dom_path.open("w", encoding="utf-8") as f:
                f.write(html)
            artifacts.append(
                SandboxArtifact(
                    sandbox_run_id=run.id,
                    artifact_type="dom_snapshot",
                    storage_path=str(dom_path),
                    created_at=datetime.utcnow(),
                )
            )
        except Exception as e:  # pragma: no cover
            log_event("dom_snapshot_error", {"error": str(e)})

        await browser.close()

    # Basic risk scoring based on signals and domain intel
    risk_score = 0.0
    summary_parts: List[str] = []
    if signals.suspicious_js_execution:
        risk_score += 0.3
        summary_parts.append("Suspicious JavaScript execution patterns observed (eval/atob hooks).")

    # Incorporate domain risk based on the final URL
    try:
        _domain, domain_risk, _reasons = evaluate_domain_for_url(db, run.url)
        risk_score += 0.3 * domain_risk
    except Exception:
        pass

    risk_score = max(0.0, min(1.0, risk_score))
    if not summary_parts:
        summary_parts.append("No high-confidence dynamic phishing behaviors detected during sandbox run.")

    return risk_score, " ".join(summary_parts), events, artifacts, signals


async def execute_sandbox_run(db: Session, run: SandboxRun) -> None:
    """
    Execute a single SandboxRun, updating its status and persisting events and artifacts.
    """
    run.status = SandboxStatus.running
    run.started_at = datetime.utcnow()
    db.add(run)
    db.commit()
    db.refresh(run)

    storage_dir = Path(SANDBOX_STORAGE_ROOT) / str(run.id)

    try:
        risk_score, summary, events, artifacts, signals = await _run_playwright(db, run, storage_dir)
        run.risk_score = risk_score
        run.summary = summary
        run.finished_at = datetime.utcnow()
        run.status = SandboxStatus.completed

        for ev in events:
            db.add(ev)
        for art in artifacts:
            db.add(art)

        db.add(run)
        db.commit()

        # If this sandbox is linked to a scan, enrich its explanation with sandbox signals.
        if run.scan_id is not None:
            scan_result = db.query(ScanResult).filter(ScanResult.scan_id == run.scan_id).first()
            if scan_result and isinstance(scan_result.explanation, dict):
                explanation = dict(scan_result.explanation)
                reasons = list(explanation.get("reasons") or [])

                sandbox_reasons: List[ExplanationReason] = []
                if signals.suspicious_js_execution:
                    sandbox_reasons.append(
                        ExplanationReason(
                            code="SANDBOX_SUSPICIOUS_JS_EXECUTION",
                            category="sandbox",
                            weight=0.25,
                            message="Dynamic analysis observed suspicious JavaScript execution behavior in a sandboxed browser.",
                        )
                    )

                # Merge sandbox reasons into stored explanation
                for r in sandbox_reasons:
                    reasons.append(
                        {
                            "code": r.code,
                            "category": r.category,
                            "weight": r.weight,
                            "message": r.message,
                        }
                    )
                explanation["reasons"] = reasons
                scan_result.explanation = explanation
                db.add(scan_result)
                db.commit()

    except Exception as e:  # pragma: no cover
        run.status = SandboxStatus.failed
        run.finished_at = datetime.utcnow()
        run.summary = f"Sandbox execution failed: {e}"
        db.add(run)
        db.commit()

