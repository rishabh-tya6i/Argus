import os
import json
import time
import pandas as pd
import numpy as np
import joblib
from typing import Dict, Any, Optional, List
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session
from ..db_models import TrainingDataset, ModelVersion, FeedbackLabel

# Identify the project root relative to this file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

class TrainingPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.model_name = "argus_phish_model"
        self.model_dir = os.path.join(PROJECT_ROOT, "ml", "models")
        os.makedirs(self.model_dir, exist_ok=True)

    def load_dataset(self) -> pd.DataFrame:
        """
        Loads training data from database into a pandas DataFrame.
        """
        results = self.db.query(TrainingDataset).all()
        if not results:
            print("No training data found in TrainingDataset table.")
            return None
        
        data = []
        for r in results:
            row = r.features.copy()
            # Map enum to int labels (safe=0, phishing/suspicious=1 as a starting point)
            label_map = {
                FeedbackLabel.safe: 0,
                FeedbackLabel.suspicious: 1,
                FeedbackLabel.phishing: 1
            }
            row["label"] = label_map.get(r.label, 0)
            row["id"] = r.id
            data.append(row)
        
        df = pd.DataFrame(data)
        # Drop non-feature columns
        X = df.drop(columns=["label", "id"], errors="ignore")
        y = df["label"]
        return X, y

    def run(self, test_size: float = 0.2) -> Optional[Dict[str, Any]]:
        """
        Runs the full training, evaluation, and versioning process.
        """
        # 1. Load data
        dataset = self.load_dataset()
        if dataset is None:
            return None
        
        X, y = dataset
        if len(X) < 10:
            print("Not enough data to start training (min 10 samples required).")
            return None
        
        # 2. Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        # 3. Define and train model
        # Using XGBoost as it's state-of-the-art for tabular data
        model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            # Handle class imbalance if needed
            scale_pos_weight=(len(y) - sum(y)) / sum(y) if sum(y) > 0 else 1.0
        )
        
        print(f"Training {self.model_name} with {len(X_train)} samples...")
        start_time = time.time()
        model.fit(X_train, y_train)
        duration = time.time() - start_time
        
        # 4. Evaluate
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(set(y_test)) > 1 else 0.0
        }
        
        # 5. Versioning
        version = f"v_{int(time.time())}"
        model_filename = f"{self.model_name}_{version}.pkl"
        model_path = os.path.join(self.model_dir, model_filename)
        
        joblib.dump(model, model_path)
        
        # 6. Save metadata
        metadata = {
            "version": version,
            "metrics": metrics,
            "dataset_size": len(X),
            "features": list(X.columns),
            "trained_at": datetime.utcnow().isoformat()
        }
        
        # 7. Register in database
        model_ref = ModelVersion(
            model_name=self.model_name,
            version=version,
            accuracy=metrics["accuracy"],
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1_score=metrics["f1_score"],
            roc_auc=metrics["roc_auc"],
            dataset_size=len(X),
            artifact_location=model_path,
            metadata_json=metadata,
            is_active=False # Deploy after validation
        )
        self.db.add(model_ref)
        self.db.commit()
        
        print(f"New model version {version} registered. Accuracy: {metrics['accuracy']:.4f}")
        return metadata

if __name__ == "__main__":
    from ..db import SessionLocal
    db = SessionLocal()
    pipeline = TrainingPipeline(db)
    pipeline.run()
    db.close()
