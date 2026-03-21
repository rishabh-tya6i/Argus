from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import re
from ..utils import tld_from_url, has_ip_in_host

class RuleEngine:
    """
    Heuristics-based detection engine for phishing links and content.
    """
    
    SUSPICIOUS_TLDS = {".tk", ".xyz", ".ru", ".top", ".ga", ".cf", ".ml", ".gq"}
    URGENT_KEYWORDS = ["verify now", "urgent", "suspended", "action required", "account locked", "unauthorized login"]
    URL_LENGTH_THRESHOLD = 100

    def __init__(self):
        pass

    def run(self, url: str, html: Optional[str] = None, email_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs rules against URL and returns score and triggered rules.
        """
        score = 0
        triggered_rules = []
        
        # 1. URL Rules
        p = urlparse(url)
        # Domain Age (Mocked or from metadata if available)
        # In a real system, we'd query WHOIS or a pre-calculated DB.
        domain_age_days = email_metadata.get("domain_age_days") if email_metadata else None
        if domain_age_days is not None and domain_age_days < 7:
            score += 40
            triggered_rules.append("Domain registered less than 7 days ago")
            
        tld = tld_from_url(url)
        if tld in self.SUSPICIOUS_TLDS:
            score += 30
            triggered_rules.append(f"Suspicious TLD: {tld}")
            
        if len(url) > self.URL_LENGTH_THRESHOLD:
            score += 10
            triggered_rules.append(f"URL length exceeds threshold ({len(url)} chars)")
            
        if has_ip_in_host(url):
            score += 50
            triggered_rules.append("IP address used instead of domain name")
            
        # 2. Content Rules
        if html:
            html_lower = html.lower()
            found_keywords = [kw for kw in self.URGENT_KEYWORDS if kw in html_lower]
            if found_keywords:
                score += 25
                triggered_rules.append(f"Urgent keywords detected: {', '.join(found_keywords)}")
                
            # Fake login form detection (Simple heuristic)
            if "<form" in html_lower and ("password" in html_lower or "login" in html_lower):
                # Check if it's on a non-HTTPS site (even though HTTPS is common now for phishing)
                if p.scheme != "https":
                    score += 50
                    triggered_rules.append("Unsecured login form detected (Non-HTTPS)")
                else:
                    # More advanced checks could be added here
                    pass

        # 3. Email Rules
        if email_metadata:
            if email_metadata.get("auth_results", {}).get("spf") == "fail" or \
               email_metadata.get("auth_results", {}).get("dkim") == "fail":
                score += 40
                triggered_rules.append("SPF/DKIM authentication failed")
                
            sender = email_metadata.get("from_address", "")
            if sender and p.netloc:
                sender_domain = sender.split("@")[-1] if "@" in sender else ""
                if sender_domain and sender_domain != p.netloc.replace("www.", ""):
                    score += 30
                    triggered_rules.append(f"Sender domain ({sender_domain}) mismatch with URL domain")

        return {
            "rule_score": min(score, 100), # Normalize to max 100 initially for scoring ease
            "raw_score": score,
            "triggered_rules": triggered_rules
        }
