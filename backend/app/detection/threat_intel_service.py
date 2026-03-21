from typing import Dict, Any, List, Optional, Set
import asyncio

class ThreatIntelService:
    """
    Service for checking URLs, IPs, and senders against threat intelligence databases.
    """
    
    # Mock data - in production, these would be loaded from a DB or external feed (e.g., PhishTank, AlienVault)
    def __init__(self):
        self._phishing_domains: Set[str] = {"example-phish.com", "login-microsoft.online", "secure-paypal-verify.tk"}
        self._blacklisted_ips: Set[str] = {"1.2.3.4", "192.168.1.100", "8.8.4.4"} # Just examples
        self._suspicious_senders: Set[str] = {"urgent@no-reply.com", "admin@update-account.tk"}
        self._cache: Dict[str, Dict[str, Any]] = {} # Simple in-memory cache for frequent lookups

    async def check(self, url: str, ip: Optional[str] = None, sender: Optional[str] = None) -> Dict[str, Any]:
        """
        Check URL, IP, and sender against threat intelligence.
        Returns risk score and match details.
        """
        # Quick cache check
        cache_key = f"{url}:{ip}:{sender}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Async check simulation
        # In a real system, you might perform parallel lookups to external APIs here.
        await asyncio.sleep(0.01) # Simulate low-latency DB/API call

        matches = []
        is_high_risk = False
        
        # Check domain lookups
        from urllib.parse import urlparse
        p = urlparse(url)
        domain = p.netloc.replace("www.", "")
        
        if domain in self._phishing_domains:
            matches.append(f"Known phishing domain: {domain}")
            is_high_risk = True
            
        # Check IP
        if ip and ip in self._blacklisted_ips:
            matches.append(f"Blacklisted IP address: {ip}")
            is_high_risk = True
            
        # Check Sender
        if sender and sender in self._suspicious_senders:
            matches.append(f"Suspicious sender identified: {sender}")
            is_high_risk = True

        result = {
            "is_high_risk": is_high_risk,
            "threat_score": 100 if is_high_risk else 0,
            "matched_intelligence": matches,
            "source": ["Local Intel", "Mock Feed"] if matches else []
        }
        
        # Limit cache size
        if len(self._cache) < 1000:
            self._cache[cache_key] = result
            
        return result

    def add_to_blacklist(self, domain: Optional[str] = None, ip: Optional[str] = None, sender: Optional[str] = None):
        """
        Manually add indicators to the threat intelligence database.
        """
        if domain: self._phishing_domains.add(domain)
        if ip: self._blacklisted_ips.add(ip)
        if sender: self._suspicious_senders.add(sender)
