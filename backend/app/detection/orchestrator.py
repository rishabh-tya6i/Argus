from typing import Dict, Any, Optional
import time
import asyncio
from sqlalchemy.orm import Session

from ..ml.predictor import Predictor
from .rule_engine import RuleEngine
from .threat_intel_service import ThreatIntelService
from .scoring import HybridScoringEngine

class DetectionOrchestrator:
    """
    Central orchestration service for hybrid phishing detection.
    Coordinates ML, rules, and threat intelligence.
    """
    def __init__(self):
        self.predictor = Predictor()
        self.rule_engine = RuleEngine()
        self.threat_intel = ThreatIntelService()
        self.scoring_engine = HybridScoringEngine()

    async def detect(
        self, 
        db: Session, 
        url: str, 
        html: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Runs the full detection pipeline.
        
        Args:
            db (Session): Database session
            url (str): The URL to scan
            html (str): The HTML content of the page (if available)
            metadata (Dict): Any additional metadata (e.g. sender, header info)
            
        Returns:
            Dict[str, Any]: Final response containing label, confidence, and reasons.
        """
        start_time = time.time()
        
        # Determine sender and IP for threat intel
        sender = metadata.get("from_address") if metadata else None
        ip = metadata.get("ip_address") if metadata else None
        
        # Use asyncio.gather for parallel execution where possible
        # Rule engine is fast, ML might be slow, Threat Intel is async
        
        # 1. Run Rule Engine (Fast)
        rule_results = self.rule_engine.run(url, html, metadata)
        
        # 2. Run Threat Intel and ML in parallel
        # Note: ML Predictor.predict() is currently synchronous. 
        # In a high-traffic environment, you'd make this async or run it in a threadpool.
        ml_task = asyncio.to_thread(self.predictor.predict, db, url, html, metadata)
        intel_task = self.threat_intel.check(url, ip, sender)
        
        # Await results
        ml_results, intel_results = await asyncio.gather(ml_task, intel_task)
        
        # 3. Calculate Final Hybrid Score
        final_results = self.scoring_engine.calculate_final_score(
            ml_results, rule_results, intel_results
        )
        
        # Performance monitoring
        latency_ms = (time.time() - start_time) * 1000
        
        # Compile response
        response = {
            "label": final_results["label"],
            "confidence": final_results["confidence"],
            "breakdown": final_results["breakdown"],
            "reasons": final_results["reasons"],
            "metadata": {
                "scan_time_ms": round(latency_ms, 2),
                "model_version": ml_results.get("version", "unknown"),
                "rules_triggered": len(rule_results.get("triggered_rules", [])),
                "intel_matches": len(intel_results.get("matched_intelligence", []))
            }
        }
        
        return response
