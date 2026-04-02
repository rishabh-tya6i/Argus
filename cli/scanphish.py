#!/usr/bin/env python3
"""
scanphish - Developer CLI for phishing risk scans (fancy edition)
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

from colorama import Fore, Style, init

init(autoreset=True)

DEFAULT_API_BASE = "http://localhost:8000/api"


# =========================
# Data Models
# =========================
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


# =========================
# Helpers
# =========================
def _color_verdict(prediction: str) -> str:
    if prediction == "phishing":
        return Fore.RED + prediction.upper()
    elif prediction == "suspicious":
        return Fore.YELLOW + prediction.upper()
    return Fore.GREEN + prediction.upper()


def _spinner():
    while True:
        for c in "|/-\\":
            yield c


# =========================
# HTTP
# =========================
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


# =========================
# Core Logic
# =========================
def run_scan(api_base: str, target_url: str, api_key: Optional[str] = None) -> ScanResult:
    endpoint = api_base.rstrip("/") + "/predict"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        resp = _post_json(endpoint, {"url": target_url}, headers=headers)
    except HTTPError as e:
        raise SystemExit(Fore.RED + f"[API ERROR {e.code}] {e.read().decode()}")
    except URLError as e:
        raise SystemExit(Fore.RED + f"[NETWORK ERROR] {e.reason}")

    return ScanResult(
        url=target_url,
        prediction=resp.get("prediction", "unknown"),
        confidence=float(resp.get("confidence", 0.0)),
        explanation=resp.get("explanation") or {},
    )


def run_security_scan(api_base: str, target_url: str, api_key: Optional[str] = None) -> SecurityScanResult:
    endpoint = api_base.rstrip("/") + "/security-scans"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        resp = _post_json(endpoint, {"url": target_url}, headers=headers)
        scan_id = resp["id"]

        print(Fore.CYAN + f"\n🔍 Scan queued (ID: {scan_id})")

        poll_endpoint = f"{endpoint}/{scan_id}"
        spin = _spinner()

        while True:
            resp = _get_json(poll_endpoint, headers=headers)
            status = resp.get("status")

            if status in ("completed", "failed"):
                break

            sys.stdout.write(Fore.CYAN + f"\rScanning... {next(spin)}")
            sys.stdout.flush()
            time.sleep(1.5)

        print("\r" + " " * 30, end="\r")  # clear line

    except HTTPError as e:
        raise SystemExit(Fore.RED + f"[API ERROR {e.code}] {e.read().decode()}")
    except URLError as e:
        raise SystemExit(Fore.RED + f"[NETWORK ERROR] {e.reason}")

    return SecurityScanResult(
        url=target_url,
        status=resp.get("status", "unknown"),
        score=resp.get("score"),
        summary=resp.get("summary"),
        issues=resp.get("issues", [])
    )


# =========================
# Pretty Printers
# =========================
def print_human_readable(result: ScanResult) -> None:
    print(Fore.CYAN + "\n=== 🔎 Phishing Scan Result ===\n")

    print(f"{Style.DIM}URL{Style.RESET_ALL}        : {result.url}")
    print(f"{Style.DIM}Verdict{Style.RESET_ALL}    : {_color_verdict(result.prediction)} "
          f"({result.confidence:.3f})")

    model_scores = result.explanation.get("model_scores") or {}
    if model_scores:
        print(f"\n{Fore.MAGENTA}Model Scores:")
        for k, v in model_scores.items():
            print(f"  • {k:<18} {v:.3f}")

    important = result.explanation.get("important_features") or []
    if important:
        print(f"\n{Fore.YELLOW}⚡ Key Signals:")
        for item in important:
            print(f"  → {item}")

    reasons = result.explanation.get("reasons") or []
    if reasons:
        print(f"\n{Fore.BLUE}🧠 Heuristics:")
        for r in reasons:
            print(f"  [{r.get('category')}/{r.get('code')}] {r.get('message')}")


def print_security_readable(result: SecurityScanResult) -> None:
    print(Fore.CYAN + "\n=== 🛡️ Website Security Report ===\n")

    print(f"{Style.DIM}URL{Style.RESET_ALL}      : {result.url}")
    print(f"{Style.DIM}Status{Style.RESET_ALL}   : {result.status.upper()}")

    if result.score is not None:
        color = Fore.GREEN if result.score >= 80 else Fore.YELLOW if result.score >= 50 else Fore.RED
        print(f"{Style.DIM}Score{Style.RESET_ALL}    : {color}{result.score}/100")

    print(f"{Style.DIM}Summary{Style.RESET_ALL}  : {result.summary}")

    if result.issues:
        print(f"\n{Fore.RED}⚠ Issues Found:")
        for issue in result.issues:
            sev = issue.get("severity", "UNKNOWN")
            desc = issue.get("description", "")
            print(f"  [{sev}] {desc}")


# =========================
# CLI Entry
# =========================
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a URL for phishing risk.")
    parser.add_argument("url", nargs="?", help="URL to scan")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key")
    parser.add_argument("--security", action="store_true")
    parser.add_argument("--fail-on", choices=["phishing", "suspicious", "never"], default="phishing")

    args = parser.parse_args(argv)

    if not args.url:
        parser.error("URL required")

    if args.security:
        result = run_security_scan(args.api_base, args.url, args.api_key)
        print_security_readable(result)

        if result.score is not None and result.score < 80 and args.fail_on != "never":
            return 1
        return 0

    result = run_scan(args.api_base, args.url, args.api_key)
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
