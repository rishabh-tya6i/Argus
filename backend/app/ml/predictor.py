import joblib
import os
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from ..db_models import ModelVersion
from .feature_extractor import FeatureExtractor

class Predictor:
    """
    Handles model loading and prediction with explainability.
    """
    _instance = None
    _model = None
    _model_version = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Predictor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.extractor = FeatureExtractor()

    def _load_active_model(self, db: Session):
        active_model_record = db.query(ModelVersion).filter(ModelVersion.is_active == True).order_by(ModelVersion.created_at.desc()).first()
        
        if not active_model_record:
            return None, None
            
        if self._model_version != active_model_record.version:
            if os.path.exists(active_model_record.artifact_location):
                self._model = joblib.load(active_model_record.artifact_location)
                self._model_version = active_model_record.version
                print(f"Loaded active model version: {self._model_version}")
            else:
                print(f"Model artifact not found at {active_model_record.artifact_location}")
                return None, None
                
        return self._model, self._model_version

    def predict(self, db: Session, url: str, html: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        model, version = self._load_active_model(db)
        
        # Extract features
        features = self.extractor.extract_all(url, html, metadata)
        
        if not model:
            # Fallback or error
            return {
                "label": "unknown",
                "confidence": 0.0,
                "version": "none",
                "reasons": ["No active ML model found"],
                "features": features
            }
            
        # Prepare features for prediction (ensure same order as training)
        # In a real system, we'd use the feature names from model metadata
        feature_names = model.get_booster().feature_names if hasattr(model, 'get_booster') else list(features.keys())
        
        # Reorder/filter features to match model expectation
        X = []
        for name in feature_names:
            X.append(features.get(name, 0))
            
        X = [X] # Batch of 1
        
        # Predict
        label_idx = int(model.predict(X)[0])
        confidence = float(model.predict_proba(X)[0][label_idx])
        
        label_map = {0: "safe", 1: "phishing"} # Simplified for v1
        
        # Explainability
        reasons = self.extractor.get_feature_reasons(features)
        
        return {
            "label": label_map.get(label_idx, "suspicious"),
            "confidence": confidence,
            "version": version,
            "reasons": reasons[:3] # Return top 3 reasons
        }
