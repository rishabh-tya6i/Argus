from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse, urljoin
import re

from bs4 import BeautifulSoup

from .schemas import ExplanationReason


_LOGIN_KEYWORDS = ("login", "signin", "sign-in", "verify", "account", "update", "password", "secure")
_REDIRECT_JS_PATTERNS = (
    "window.location",
    "location.href",
    "location.replace",
    "document.location",
)
_OBFUSCATION_PATTERNS = (
    "eval(",
    "Function(",
    "atob(",
    "unescape(",
    "fromCharCode(",
)


def _analyze_url(url: str) -> List[ExplanationReason]:
    reasons: List[ExplanationReason] = []
    parsed = urlparse(url)
    host = parsed.hostname or ""
    full = url.lower()

    # Long + complex URL with many digits is often suspicious
    if len(full) > 120:
        digit_ratio = sum(ch.isdigit() for ch in full) / len(full)
        if digit_ratio > 0.25:
            reasons.append(
                ExplanationReason(
                    code="SUSPICIOUS_URL_COMPLEXITY",
                    category="url",
                    weight=0.15,
                    message=(
                        "URL is unusually long and contains a high proportion of digits, "
                        "a common pattern in phishing links used to evade filters."
                    ),
                )
            )

    # Login-related keywords in path/query but on an unfamiliar host
    if any(k in full for k in _LOGIN_KEYWORDS) and host.count(".") >= 2:
        reasons.append(
            ExplanationReason(
                code="LOGIN_KEYWORDS_ON_NON_ROOT_DOMAIN",
                category="url",
                weight=0.1,
                message=(
                    "URL path contains login or account-related keywords while being served "
                    "from a subdomain, which is a common pattern in credential harvesting sites."
                ),
            )
        )

    # Punycode / potential homograph indicator
    if "xn--" in host:
        reasons.append(
            ExplanationReason(
                code="POTENTIAL_HOMOGRAPH_DOMAIN",
                category="domain",
                weight=0.2,
                message=(
                    "Domain uses punycode encoding (xn-- prefix), which is often leveraged "
                    "for homograph attacks that visually impersonate legitimate brands."
                ),
            )
        )

    return reasons


def _analyze_html(url: str, html: str) -> List[ExplanationReason]:
    reasons: List[ExplanationReason] = []
    if not html:
        return reasons

    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(url)
    origin_host = parsed.hostname or ""

    # Credential harvesting forms: password fields posting to a different domain
    for form in soup.find_all("form"):
        inputs = form.find_all("input")
        has_password = any((inp.get("type") or "").lower() == "password" for inp in inputs)
        if not has_password:
            continue

        action = form.get("action") or ""
        if not action:
            continue
        target = urljoin(url, action)
        target_host = urlparse(target).hostname or ""
        if target_host and target_host != origin_host:
            reasons.append(
                ExplanationReason(
                    code="CREDENTIAL_POST_TO_DIFFERENT_DOMAIN",
                    category="form",
                    weight=0.25,
                    message=(
                        "Login form containing password inputs posts credentials to a domain "
                        "different from the page origin, which is a strong indicator of "
                        "credential harvesting behavior."
                    ),
                )
            )
            break

    # Hidden or off-screen forms with password fields
    for form in soup.find_all("form"):
        style = (form.get("style") or "").lower()
        if "display:none" in style or "visibility:hidden" in style or "opacity:0" in style:
            if form.find("input", {"type": "password"}):
                reasons.append(
                    ExplanationReason(
                        code="HIDDEN_CREDENTIAL_FORM",
                        category="form",
                        weight=0.2,
                        message=(
                            "Hidden form containing password inputs detected; attackers often "
                            "use invisible forms to capture credentials or session tokens."
                        ),
                    )
                )
                break

    # Meta refresh redirects
    for meta in soup.find_all("meta"):
        http_equiv = (meta.get("http-equiv") or meta.get("http_equiv") or "").lower()
        if http_equiv == "refresh":
            reasons.append(
                ExplanationReason(
                    code="META_REFRESH_REDIRECT",
                    category="redirect",
                    weight=0.1,
                    message=(
                        "Page includes a meta refresh redirect, which can be used to quickly "
                        "send users to a different phishing destination after initial load."
                    ),
                )
            )
            break

    # Script-based redirects and obfuscation patterns
    scripts_text = " ".join(script.get_text(separator=" ") for script in soup.find_all("script"))
    lowered = scripts_text.lower()

    if any(pat in lowered for pat in _REDIRECT_JS_PATTERNS):
        reasons.append(
            ExplanationReason(
                code="JAVASCRIPT_REDIRECT_LOGIC",
                category="script",
                weight=0.1,
                message=(
                    "Inline JavaScript contains logic that changes window.location or similar "
                    "APIs, indicating potential redirect chains used in phishing flows."
                ),
            )
        )

    if any(pat in lowered for pat in _OBFUSCATION_PATTERNS):
        reasons.append(
            ExplanationReason(
                code="OBFUSCATED_JAVASCRIPT_PATTERNS",
                category="script",
                weight=0.15,
                message=(
                    "JavaScript contains patterns such as eval/Function/atob that are often "
                    "used to obfuscate malicious code and hide credential exfiltration logic."
                ),
            )
        )

    # Long base64-like strings embedded in scripts
    base64_like = re.findall(r"[A-Za-z0-9+/]{80,}={0,2}", scripts_text)
    if base64_like:
        reasons.append(
            ExplanationReason(
                code="EMBEDDED_ENCODED_PAYLOAD",
                category="script",
                weight=0.1,
                message=(
                    "Detected long base64-like encoded blobs in JavaScript, which may contain "
                    "hidden payloads or exfiltration logic."
                ),
            )
        )

    return reasons


def generate_heuristic_reasons(url: str, html: Optional[str]) -> List[ExplanationReason]:
    """
    Generate deterministic, explainable security reasons based on URL and HTML.

    This complements the ML model scores and provides developer-friendly insight
    into suspicious behaviors such as credential harvesting forms, redirects, and
    obfuscated JavaScript.
    """
    reasons: List[ExplanationReason] = []
    reasons.extend(_analyze_url(url))
    if html:
        reasons.extend(_analyze_html(url, html))
    return reasons

