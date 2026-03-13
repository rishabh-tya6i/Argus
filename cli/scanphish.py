#!/usr/bin/env python3
"""
scanphish - Developer CLI for phishing risk scans.

This tool sends URLs to the backend phishing detection API and prints a
developer-focused summary, including model confidence and heuristic
explanations (hidden forms, obfuscated JS, redirects, etc.).

Intended usage:

    scanphish https://example.com
    scanphish https://example.com --api-base http://localhost:8000/api

The CLI is designed to integrate easily into CI pipelines by returning a
non-zero exit code when high-risk phishing is detected (configurable via
--fail-on).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError


DEFAULT_API_BASE = "http://localhost:8000/api"


@dataclass
class ScanResult:
    url: str
    prediction: str
    confidence: float
    explanation: Dict[str, Any]


@dataclass
class SecurityScanResult:
    url: str
    status: str
    score: Optional[int]
    summary: Optional[str]
    issues: List[Dict[str, Any]]


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    with urlrequest.urlopen(req, timeout=20) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def _get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req = urlrequest.Request(url, headers=headers or {})
    with urlrequest.urlopen(req, timeout=20) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def run_scan(api_base: str, target_url: str, api_key: Optional[str] = None) -> ScanResult:
    endpoint = api_base.rstrip("/") + "/predict"
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = _post_json(endpoint, {"url": target_url}, headers=headers)
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"[scanphish] API error {e.code}: {msg}")
    except URLError as e:
        raise SystemExit(f"[scanphish] Failed to reach API at {endpoint}: {e.reason}")

    return ScanResult(
        url=target_url,
        prediction=resp.get("prediction", "unknown"),
        confidence=float(resp.get("confidence", 0.0)),
        explanation=resp.get("explanation") or {},
    )


def run_security_scan(api_base: str, target_url: str, api_key: Optional[str] = None) -> SecurityScanResult:
    endpoint = api_base.rstrip("/") + "/security-scans"
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        # 1. Enqueue
        resp = _post_json(endpoint, {"url": target_url}, headers=headers)
        scan_id = resp["id"]
        print(f"[*] Security scan queued with ID: {scan_id}")

        # 2. Poll
        poll_endpoint = f"{endpoint}/{scan_id}"
        while True:
            resp = _get_json(poll_endpoint, headers=headers)
            status = resp.get("status")
            if status in ("completed", "failed"):
                break
            time.sleep(2)
            print(".", end="", flush=True)
        print()
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"[scanphish security] API error {e.code}: {msg}")
    except URLError as e:
        raise SystemExit(f"[scanphish security] Failed to reach API at {endpoint}: {e.reason}")

    return SecurityScanResult(
        url=target_url,
        status=resp.get("status", "unknown"),
        score=resp.get("score"),
        summary=resp.get("summary"),
        issues=resp.get("issues", [])
    )


def print_human_readable(result: ScanResult) -> None:
    print(f"URL          : {result.url}")
    print(f"Verdict      : {result.prediction.upper()}  (confidence={result.confidence:.3f})")

    model_scores = result.explanation.get("model_scores") or {}
    print("Model scores : ", end="")
    parts = []
    for name in ("url_model", "html_model", "visual_model", "classical_model"):
        if name in model_scores:
            parts.append(f"{name}={model_scores[name]:.3f}")
    print(", ".join(parts) if parts else "n/a")

    important = result.explanation.get("important_features") or []
    if important:
        print("\nKey signals  :")
        for item in important:
            print(f"  - {item}")

    reasons: List[Dict[str, Any]] = result.explanation.get("reasons") or []
    visual_impersonations = [r for r in reasons if r.get("code") == "BRAND_IMPERSONATION_DETECTED"]
    other_reasons = [r for r in reasons if r.get("code") != "BRAND_IMPERSONATION_DETECTED"]

    if visual_impersonations:
        print("\n=== VISUAL BRAND IMPERSONATION WARNING ===")
        for r in visual_impersonations:
            msg = r.get("message", "Visual similarity detected to known brand")
            print(f"  [ATTENTION] {msg}")
        print("==========================================")

    if other_reasons:
        print("\nHeuristic reasons:")
        for r in other_reasons:
            code = r.get("code", "UNKNOWN")
            category = r.get("category", "general")
            weight = r.get("weight", 0.0)
            message = r.get("message", "")
            print(f"  [{category}/{code} | weight={weight:.2f}] {message}")


def print_security_readable(result: SecurityScanResult) -> None:
    print("--- Website Security Scanner ---")
    print(f"URL          : {result.url}")
    print(f"Status       : {result.status.upper()}")
    
    if result.status == "failed":
        print(f"Summary      : {result.summary}")
        return

    print(f"Score        : {result.score}/100")
    print(f"Summary      : {result.summary}")

    if result.issues:
        print("\nIdentified Issues:")
        for item in result.issues:
            sev = item.get("severity", "UNKNOWN")
            cat = item.get("category", "unknown")
            desc = item.get("description", "")
            rem = item.get("remediation", "")
            print(f"  [{sev}] {cat}: {desc}")
            if rem:
                print(f"    -> Remediation: {rem}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a URL for phishing risk using the backend detection API.")
    parser.add_argument("url", nargs="?", default=None, help="URL to scan, e.g. https://example.com")
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"Base URL for the detection API (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key or bearer token to include as Authorization header.",
    )
    parser.add_argument(
        "--security",
        action="store_true",
        help="Run an async Website Security Scan using Playwright instead of a prediction scan.",
    )
    parser.add_argument(
        "--intel",
        action="store_true",
        help="Run local threat intel ingestion jobs (CT and NRD feeds) for testing.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["phishing", "suspicious", "never"],
        default="phishing",
        help=(
            "Exit with non-zero status when the verdict is at or above this level. "
            "Use 'never' to always exit 0 (useful for local exploration)."
        ),
    )

    args = parser.parse_args(argv)

    if args.intel:
        print("[*] Running Threat Intelligence Ingestion...")
        try:
            from backend.app.workers.ct_log_worker import main as ct_main
            from backend.app.workers.nrd_worker import main as nrd_main
            from backend.app.workers.passive_dns_worker import main as pdns_main
            
            print(" -> Running CT Log Monitor")
            ct_main(run_forever=False)
            print(" -> Running NRD Monitor")
            nrd_main()
            print(" -> Running Passive DNS checks")
            pdns_main()
            
            print("[OK] Threat Intelligence ingestion complete.")
            return 0
        except ImportError as e:
            print(f"[-] Could not import worker modules. Ensure you're running from the project root: {e}")
            return 1

    if not args.url:
        parser.error("url is required for scanning commands")

    if args.security:
        result = run_security_scan(api_base=args.api_base, target_url=args.url, api_key=args.api_key)
        print_security_readable(result)
        if result.status == "failed" or (result.score is not None and result.score < 80 and args.fail_on != "never"):
            return 1
        return 0
    else:
        result = run_scan(api_base=args.api_base, target_url=args.url, api_key=args.api_key)
        print_human_readable(result)

        if args.fail_on == "never":
            return 0

        if result.prediction == "phishing":
            return 1
        if result.prediction == "suspicious" and args.fail_on == "suspicious":
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

