from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple, Any
from urllib.parse import urlparse

import tldextract
import whois
import dns.resolver

from sqlalchemy.orm import Session

from ..db_models import DomainReputation, ThreatFeedEntry, TenantDomainWatch
from ..schemas import ExplanationReason


SUSPICIOUS_TLDS = {
    "xyz",
    "top",
    "click",
    "link",
    "loan",
    "download",
    "kim",
    "men",
    "work",
    "info",
    "biz",
}


@dataclass
class DomainInfo:
    domain: str
    age_days: Optional[int]
    registrar: Optional[str]
    whois_privacy_enabled: Optional[bool]
    in_threat_feed: bool
    flags: Dict[str, bool]


def _now() -> datetime:
    return datetime.utcnow()


def _extract_domain_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return host.lower() or None


def normalize_domain(domain: str) -> str:
    """Extract base domain and remove wildcards."""
    domain = domain.lower()
    if domain.startswith("*."):
        domain = domain[2:]
    ext = tldextract.extract(domain)
    # Reconstruct base domain. Use f"{ext.domain}.{ext.suffix}"
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return domain


def get_domain_enrichment(domain: str) -> Dict[str, Any]:
    """Fetch WHOIS and DNS intelligence for a domain."""
    enrichment: Dict[str, Any] = {}
    
    # 1. IP Lookup
    try:
        answers = dns.resolver.resolve(domain, 'A')
        ips = [rdata.address for rdata in answers]
        if ips:
            enrichment['ip_address'] = ips[0]
            # Simple placeholder for ASN without a full ASN database
            enrichment['asn'] = "AS_UNKNOWN" 
    except Exception:
        pass

    # 2. WHOIS Lookup
    try:
        w = whois.whois(domain)
        if w:
            if w.creation_date:
                creation = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                if isinstance(creation, datetime):
                    age_days = (datetime.utcnow() - creation).days
                    # Prevent negative age due to timezone issues
                    enrichment['domain_age_days'] = max(0, age_days)
            if w.registrar:
                enrichment['registrar'] = w.registrar if isinstance(w.registrar, str) else str(w.registrar)
    except Exception:
        pass
    
    return enrichment


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[m][n]


def detect_typosquatting(domain: str, brand_domains: Sequence[str]) -> List[Tuple[str, float]]:
    """
    Detect potential typosquatting where `domain` is visually or edit-distance
    similar to any of the given brand domains.

    Returns a list of (brand_domain, score) pairs where score ∈ (0,1].
    """
    hits: List[Tuple[str, float]] = []
    domain_l = domain.lower()

    def core_name(d: str) -> str:
        # naive: strip first label from host, drop TLD
        parts = d.split(".")
        if len(parts) >= 2:
            return parts[-2]
        return parts[0]

    domain_core = core_name(domain_l)

    for brand in brand_domains:
        brand_l = brand.lower()
        brand_core = core_name(brand_l)
        dist = _levenshtein(domain_core, brand_core)
        max_len = max(len(domain_core), len(brand_core)) or 1
        similarity = 1.0 - (dist / max_len)
        if similarity >= 0.7 and dist <= 2:
            hits.append((brand_l, similarity))
            continue

        # Pattern-based phishing: login-brand.com, secure-brand-auth.com, etc.
        if brand_core in domain_core and any(
            prefix in domain_core for prefix in ("login", "secure", "auth", "verify")
        ):
            hits.append((brand_l, 0.8))

    return hits


def detect_homograph(domain: str) -> bool:
    """
    Basic homograph detection:
    - Punycode (xn--)
    - Non-ASCII characters in label.
    """
    domain_l = domain.lower()
    if "xn--" in domain_l:
        return True
    return any(ord(ch) > 127 for ch in domain_l)


def get_domain_info(db: Session, domain: str) -> DomainInfo:
    repo = db.query(DomainReputation).filter(DomainReputation.domain == domain).first()
    if repo is None:
        now = _now()
        repo = DomainReputation(
            domain=domain,
            risk_score=0.0,
            domain_age_days=None,
            registrar=None,
            whois_privacy_enabled=None,
            flags={},
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    in_threat_feed = (
        db.query(ThreatFeedEntry).filter(ThreatFeedEntry.domain == domain).first() is not None
    )

    flags = dict(repo.flags or {})
    flags["in_threat_feed"] = in_threat_feed
    repo.flags = flags
    repo.last_seen_at = _now()
    db.add(repo)
    db.commit()

    return DomainInfo(
        domain=repo.domain,
        age_days=repo.domain_age_days,
        registrar=repo.registrar,
        whois_privacy_enabled=repo.whois_privacy_enabled,
        in_threat_feed=in_threat_feed,
        flags=flags,
    )


def calculate_domain_risk(db: Session, domain: str) -> Tuple[float, List[ExplanationReason]]:
    """
    Calculate a domain-level risk score in [0,1] and explanatory reasons based
    on reputation data and simple heuristics.
    """
    info = get_domain_info(db, domain)
    reasons: List[ExplanationReason] = []
    score = 0.0

    tld = domain.split(".")[-1] if "." in domain else domain
    is_suspicious_tld = tld in SUSPICIOUS_TLDS
    is_homograph = detect_homograph(domain)

    # Newly registered / very young domain
    if info.age_days is not None and info.age_days < 7:
        score += 0.3
        reasons.append(
            ExplanationReason(
                code="DOMAIN_NEWLY_REGISTERED",
                category="domain",
                weight=0.3,
                message=f"Domain registered {info.age_days} days ago, which is highly correlated with phishing campaigns.",
            )
        )

    if is_suspicious_tld:
        score += 0.15
        reasons.append(
            ExplanationReason(
                code="DOMAIN_SUSPICIOUS_TLD",
                category="domain",
                weight=0.15,
                message=f"Domain uses a high-risk top-level domain '.{tld}' frequently abused in phishing.",
            )
        )

    if info.in_threat_feed:
        score += 0.4
        reasons.append(
            ExplanationReason(
                code="DOMAIN_IN_THREAT_FEED",
                category="intel",
                weight=0.4,
                message="Domain appears in one or more phishing/threat intelligence feeds.",
            )
        )

    if is_homograph:
        score += 0.25
        reasons.append(
            ExplanationReason(
                code="DOMAIN_HOMOGRAPH",
                category="domain",
                weight=0.25,
                message="Domain uses punycode or non-ASCII characters, which can indicate a homograph attack.",
            )
        )

    # Clamp score into [0,1]
    score = max(0.0, min(1.0, score))

    # Persist aggregated risk score
    repo = db.query(DomainReputation).filter(DomainReputation.domain == domain).first()
    if repo is not None:
        repo.risk_score = max(repo.risk_score, score)
        repo.flags = {**(repo.flags or {}), "homograph": is_homograph, "suspicious_tld": is_suspicious_tld}
        repo.last_seen_at = _now()
        db.add(repo)
        db.commit()

    return score, reasons


def evaluate_domain_for_url(db: Session, url: str) -> Tuple[Optional[str], float, List[ExplanationReason]]:
    """
    Convenience wrapper for the detection pipeline:

    - Extract domain from the URL.
    - Compute domain risk score and explanation reasons.
    """
    domain = _extract_domain_from_url(url)
    if not domain:
        return None, 0.0, []
    score, reasons = calculate_domain_risk(db, domain)
    return domain, score, reasons

