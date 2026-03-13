import pytest
from backend.app.services.domain_intel import detect_homograph, detect_typosquatting
from backend.app.schemas import ExplanationReason

def test_detect_homograph():
    assert detect_homograph("example.com") is False
    assert detect_homograph("xn--exmple-dua.com") is True
    assert detect_homograph("exämple.com") is True
    assert detect_homograph("login-şecure.com") is True

def test_detect_typosquatting():
    brands = ["paypal.com", "microsoft.com", "apple.com"]
    
    # Exact match distance 1
    hits = detect_typosquatting("paypa1.com", brands)
    assert len(hits) == 1
    assert hits[0][0] == "paypal.com"
    assert hits[0][1] > 0.8
    
    # Distance 2
    hits = detect_typosquatting("micrsoft.com", brands)
    assert len(hits) == 1
    assert hits[0][0] == "microsoft.com"
    assert hits[0][1] > 0.7
    
    # Pattern based match
    hits = detect_typosquatting("login-apple-auth.com", brands)
    assert len(hits) == 1
    assert hits[0][0] == "apple.com"
    assert hits[0][1] == 0.8  # forced score for pattern hits
    
    # No match
    hits = detect_typosquatting("random-site.com", brands)
    assert len(hits) == 0

def test_detect_typosquatting_long_domain():
    brands = ["bankofamerica.com"]
    hits = detect_typosquatting("secure-login-bankofamerica.com", brands)
    assert len(hits) == 1
    assert hits[0][0] == "bankofamerica.com"
    assert hits[0][1] == 0.8
