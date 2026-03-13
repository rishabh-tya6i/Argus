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


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
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
    if reasons:
        print("\nHeuristic reasons:")
        for r in reasons:
            code = r.get("code", "UNKNOWN")
            category = r.get("category", "general")
            weight = r.get("weight", 0.0)
            message = r.get("message", "")
            print(f"  [{category}/{code} | weight={weight:.2f}] {message}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a URL for phishing risk using the backend detection API.")
    parser.add_argument("url", help="URL to scan, e.g. https://example.com")
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
        "--fail-on",
        choices=["phishing", "suspicious", "never"],
        default="phishing",
        help=(
            "Exit with non-zero status when the verdict is at or above this level. "
            "Use 'never' to always exit 0 (useful for local exploration)."
        ),
    )

    args = parser.parse_args(argv)

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

