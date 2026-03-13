from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re
import pandas as pd

from .utils import tld_from_url, domain_tokens_entropy, count_query_params, has_ip_in_host, ratio_digits


form_regex = re.compile(r"<form[\s>]", re.IGNORECASE)
input_regex = re.compile(r"<input[\s>]", re.IGNORECASE)


def extract_features(url: str, html: Optional[str]) -> pd.DataFrame:
    p = urlparse(url)
    host = p.hostname or ""
    path = p.path or ""
    s = url or ""
    https = p.scheme.lower() == "https"
    html_text = html if isinstance(html, str) else ""
    features: Dict[str, Any] = {
        "length": len(s),
        "count_dots": s.count("."),
        "count_hyphens": s.count("-"),
        "has_ip": 1 if has_ip_in_host(url) else 0,
        "ratio_digits": ratio_digits(s),
        "presence_of_https": 1 if https else 0,
        "count_query_params": count_query_params(url),
        "domain_tokens_entropy": domain_tokens_entropy(url),
        "tld": tld_from_url(url),
        "form_count": len(form_regex.findall(html_text)) if html_text else 0,
        "input_count": len(input_regex.findall(html_text)) if html_text else 0,
        "html_text": html_text,
    }
    return pd.DataFrame([features])