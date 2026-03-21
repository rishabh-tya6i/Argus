import os
import time
import logging
import joblib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..db_models import ModelVersion

logger = logging.getLogger(__name__)

# Identify the project root relative to this file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

class ModelLoader:
    def __init__(self, refresh_interval: int = 300):
        """
        Manages loading and caching of active ML models from the database registry.
        
        Args:
            refresh_interval (int): Seconds between automatic checks for new active models.
        """
        self.loaded_models: Dict[str, Dict[str, Any]] = {}  # model_name -> {model, version_id, version_str}
        self.last_refresh = 0
        self.refresh_interval = refresh_interval
        
    def get_model(self, model_name: str = "ensemble") -> Optional[Any]:
        """
        Retrieves the current active model from memory. 
        Refreshes if the cache is stale or if the model isn't loaded.
        """
        current_time = time.time()
        if (current_time - self.last_refresh > self.refresh_interval) or (model_name not in self.loaded_models):
            self.refresh_active_models()
            
        data = self.loaded_models.get(model_name)
        return data["model"] if data else None

    def refresh_active_models(self):
        """
        Synchronizes memory with the ModelVersion table. 
        Loads only what's changed or missing.
        """
        db = SessionLocal()
        try:
            # Get latest active version for each model_name
            active_versions = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
            
            for version_record in active_versions:
                name = version_record.model_name
                
                # If already loaded and same version, skip
                if name in self.loaded_models and self.loaded_models[name]["version_id"] == version_record.id:
                    continue
                
                # Fetch and load new model
                try:
                    artifact_path = os.path.join(PROJECT_ROOT, version_record.artifact_location)
                    if not os.path.exists(artifact_path):
                        logger.warning(f"Active model artifact {version_record.artifact_location} not found on disk. Skipping.")
                        continue
                        
                    new_model = joblib.load(artifact_path)
                    
                    # Update cache (Fallback is handled by not deleting until successful load)
                    self.loaded_models[name] = {
                        "model": new_model,
                        "version_id": version_record.id,
                        "version_str": version_record.version
                    }
                    logger.info(f"Model '{name}' updated to version {version_record.version}")
                except Exception as exc:
                    logger.error(f"Critical error loading model '{name}' (v{version_record.version}): {exc}")
                    # Note: Previous version remains in self.loaded_models[name] so service stays up
            
            self.last_refresh = time.time()
        except Exception as exc:
            logger.error(f"Failed to query model registry: {exc}")
        finally:
            db.close()

# Global singleton
model_loader = ModelLoader()

def get_active_model(model_name: str = "ensemble"):
    return model_loader.get_model(model_name)
