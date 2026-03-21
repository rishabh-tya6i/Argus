import re
import math
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import tldextract
from datetime import datetime
import numpy as np

class FeatureExtractor:
    """
    Production-grade feature extractor for phishing detection.
    Extracts URL, Content, and Metadata features.
    """
    
    def __init__(self):
        self.suspicious_keywords = ["urgent", "verify", "account", "update", "bank", "login", "secure", "action", "required"]
        self.form_regex = re.compile(r"<form[\s>]", re.IGNORECASE)
        self.input_regex = re.compile(r"<input[\s>]", re.IGNORECASE)
        self.urgent_regex = re.compile(r"(urgent|verify|action required|suspended|unauthorized)", re.IGNORECASE)

    def extract_url_features(self, url: str) -> Dict[str, Any]:
        parsed = urlparse(url)
        extracted = tldextract.extract(url)
        
        hostname = parsed.hostname or ""
        path = parsed.path or ""
        query = parsed.query or ""
        
        return {
            "url_length": len(url),
            "host_length": len(hostname),
            "path_length": len(path),
            "query_length": len(query),
            "num_dots": url.count("."),
            "num_hyphens": url.count("-"),
            "num_special_chars": len(re.findall(r"[@_!#$%^&*()<>?/\\|}{~:]", url)),
            "is_https": 1 if parsed.scheme.lower() == "https" else 0,
            "has_ip": 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname) else 0,
            "domain_entropy": self._calculate_entropy(extracted.domain),
            "num_subdomains": len(extracted.subdomain.split(".")) if extracted.subdomain else 0,
            "has_suspicious_tld": 1 if extracted.suffix in ["zip", "mov", "app", "xyz", "top"] else 0,
            "num_digits": sum(c.isdigit() for c in url),
            "ratio_digits": sum(c.isdigit() for c in url) / len(url) if len(url) > 0 else 0,
        }

    def extract_content_features(self, html: Optional[str], text: Optional[str] = None) -> Dict[str, Any]:
        if not html:
            return {
                "num_forms": 0,
                "num_inputs": 0,
                "has_urgent_language": 0,
                "num_suspicious_keywords": 0,
                "html_length": 0
            }
        
        content = text or html
        return {
            "num_forms": len(self.form_regex.findall(html)),
            "num_inputs": len(self.input_regex.findall(html)),
            "has_urgent_language": 1 if self.urgent_regex.search(content) else 0,
            "num_suspicious_keywords": sum(1 for word in self.suspicious_keywords if word in content.lower()),
            "html_length": len(html)
        }

    def extract_metadata_features(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "is_mobile": 1 if "mobile" in metadata.get("user_agent", "").lower() else 0,
            "has_known_ip": 1 if metadata.get("ip_address") else 0,
            "scan_source": metadata.get("source", "unknown"),
        }

    def extract_all(self, url: str, html: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        features = {}
        features.update(self.extract_url_features(url))
        features.update(self.extract_content_features(html))
        if metadata:
            features.update(self.extract_metadata_features(metadata))
        return features

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        probabilities = [float(text.count(c)) / len(text) for c in set(text)]
        entropy = -sum(p * math.log(p, 2) for p in probabilities)
        return entropy

    def get_feature_reasons(self, features: Dict[str, Any]) -> List[str]:
        """
        Human-readable explanation based on features.
        """
        reasons = []
        if features.get("url_length", 0) > 100:
            reasons.append("URL is unusually long")
        if features.get("has_ip") == 1:
            reasons.append("URL uses an IP address instead of a domain name")
        if features.get("num_dots", 0) > 4:
            reasons.append("Unusual number of subdomains or dots")
        if features.get("has_urgent_language") == 1:
            reasons.append("Contains urgent or suspicious language")
        if features.get("num_forms", 0) > 0 and features.get("is_https") == 0:
            reasons.append("Form detected over unencrypted (HTTP) connection")
        if features.get("has_suspicious_tld") == 1:
            reasons.append("Uses a TLD often associated with phishing or malware")
        
        return reasons
