from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError


DEFAULT_API_BASE = "http://localhost:8000/api"


@dataclass
class DetectionResult:
    prediction: str
    confidence: float
    explanation: Dict[str, Any]


class PhishingClient:
    """
    Minimal Python SDK client for the phishing detection API.

    Example:

        from phishguard import PhishingClient

        client = PhishingClient(api_base="https://api.example.com/api", api_key="...secret...")
        result = client.detect_phishing("https://example.com")
        print(result.prediction, result.confidence)
    """

    def __init__(self, api_base: str = DEFAULT_API_BASE, api_key: Optional[str] = None) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base}{path}"
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urlrequest.Request(url, data=data, headers=headers)
        try:
            with urlrequest.urlopen(req, timeout=20) as resp:
                body = resp.read()
        except HTTPError as e:
            msg = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Detection API error {e.code}: {msg}") from e
        except URLError as e:
            raise RuntimeError(f"Failed to reach detection API at {url}: {e.reason}") from e

        return json.loads(body.decode("utf-8"))

    def detect_phishing(self, url: str, html: Optional[str] = None, screenshot: Optional[str] = None) -> DetectionResult:
        payload: Dict[str, Any] = {"url": url}
        if html is not None:
            payload["html"] = html
        if screenshot is not None:
            payload["screenshot"] = screenshot

        resp = self._post("/predict", payload)
        return DetectionResult(
            prediction=resp.get("prediction", "unknown"),
            confidence=float(resp.get("confidence", 0.0)),
            explanation=resp.get("explanation") or {},
        )


def detect_phishing(url: str, api_base: str = DEFAULT_API_BASE, api_key: Optional[str] = None) -> DetectionResult:
    """
    Convenience function for one-off scans:

        from phishguard import detect_phishing

        result = detect_phishing("https://example.com")
    """
    client = PhishingClient(api_base=api_base, api_key=api_key)
    return client.detect_phishing(url)

