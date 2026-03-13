import math
import re
from urllib.parse import urlparse, parse_qs


ip_regex = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def tld_from_url(url: str) -> str:
    p = urlparse(url)
    host = p.hostname or ""
    parts = host.split(".")
    return parts[-1] if parts else ""


def domain_tokens_entropy(url: str) -> float:
    p = urlparse(url)
    host = p.hostname or ""
    if not host:
        return 0.0
    freq = {}
    for ch in host:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(host)
    ent = 0.0
    for c in freq.values():
        p = c / total
        ent -= p * math.log(p, 2)
    return ent


def count_query_params(url: str) -> int:
    p = urlparse(url)
    q = parse_qs(p.query)
    return len(q)


def has_ip_in_host(url: str) -> bool:
    p = urlparse(url)
    host = p.hostname or ""
    return bool(ip_regex.match(host))


def ratio_digits(s: str) -> float:
    if not s:
        return 0.0
    digits = sum(ch.isdigit() for ch in s)
    return digits / len(s)