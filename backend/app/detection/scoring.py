from typing import Dict, Any, List

class HybridScoringEngine:
    """
    Combines results from multiple detection layers (ML, Rules, Threat Intel) 
    into a single risk score and label.
    """
    
    # Thresholds for labeling
    SAFE_THRESHOLD = 0.3
    SUSPICIOUS_THRESHOLD = 0.6
    PHISHING_THRESHOLD = 0.8 # Anything above this is phishing

    def __init__(self):
        pass

    def calculate_final_score(
        self, 
        ml_results: Dict[str, Any], 
        rule_results: Dict[str, Any], 
        threat_intel_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates final risk score and generates a phishing label.
        
        Formula:
        final_score = (ml_confidence * 0.5) + (rule_score_norm * 0.3) + (threat_intel_score * 0.2)
        """
        # ML Confidence (assuming [0, 1])
        # If ML says safe, confidence should be weighted appropriately.
        # Let's say confidence is for the 'phishing' label.
        ml_score = ml_results.get("confidence", 0.0)
        if ml_results.get("label") == "safe":
            ml_score = 1.0 - ml_score # Low phishing risk if ML says safe with high confidence
            
        # Rule score normalization (max score of 100 becomes 1.0)
        rule_score_norm = min(rule_results.get("rule_score", 0), 100) / 100.0
        
        # Threat Intel score (0 or 100 becomes 0 or 1.0)
        threat_intel_score = min(threat_intel_results.get("threat_score", 0), 100) / 100.0
        
        # Weighted hybrid calculation
        final_score = (
            (ml_score * 0.5) + 
            (rule_score_norm * 0.3) + 
            (threat_intel_score * 0.2)
        )
        
        # Determine label
        if final_score >= self.PHISHING_THRESHOLD or threat_intel_results.get("is_high_risk"):
            label = "phishing"
        elif final_score >= self.SUSPICIOUS_THRESHOLD:
            label = "suspicious"
        else:
            label = "safe"
            
        # Compile explanations/reasons
        reasons = []
        if threat_intel_results.get("matched_intelligence"):
            reasons.extend(threat_intel_results.get("matched_intelligence", []))
            
        if rule_results.get("triggered_rules"):
            reasons.extend(rule_results.get("triggered_rules", []))
            
        if ml_results.get("label") == "phishing" and ml_results.get("confidence", 0) > 0.7:
             reasons.append(f"ML model confidence: {int(ml_results.get('confidence', 0) * 100)}%")
        elif ml_results.get("label") == "safe" and ml_results.get("confidence", 0) > 0.7:
             reasons.append(f"ML model flags as safe: {int(ml_results.get('confidence', 0) * 100)}% confidence")

        return {
            "label": label,
            "confidence": round(final_score, 4),
            "breakdown": {
                "ml": round(ml_score, 4),
                "rules": round(rule_score_norm, 4),
                "threat_intel": round(threat_intel_score, 4)
            },
            "reasons": reasons[:4] # Top 4 reasons for brevity
        }
