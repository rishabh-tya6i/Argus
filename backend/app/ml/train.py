import os
import json
import time
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

# Identify the project root relative to this file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

def train_and_evaluate(dataset_path: str, model_name: str = "ensemble"):
    """
    Trains a phishing detection model using the provided dataset.
    Follows a 70/15/15 split and saves artifacts with performance metrics.
    """
    if not os.path.exists(dataset_path):
        print(f"Dataset not found: {dataset_path}")
        return None

    # 1. Load dataset
    df = pd.read_parquet(dataset_path)
    
    # Separate features and target
    # We drop metadata columns not useful for training (scan_id, url)
    X = df.drop(columns=["label", "scan_id", "url"], errors="ignore")
    y = (df["label"] == "phishing").astype(int)
    
    # 2. Split: Train (70%), Remainder (30%) -> Val (15%), Test (15%)
    X_train, X_rem, y_train, y_rem = train_test_split(X, y, train_size=0.7, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_rem, y_rem, test_size=0.5, random_state=42)
    
    # 3. Define Pipeline
    # Using features extracted in features.py
    numeric_features = [
        "length", "count_dots", "count_hyphens", "has_ip", "ratio_digits", 
        "presence_of_https", "count_query_params", "domain_tokens_entropy", 
        "form_count", "input_count"
    ]
    html_feature = "html_text"

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("html", TfidfVectorizer(max_features=1000), html_feature),
        ],
        remainder="drop"
    )

    # Gradient Boosting usually performs well for these types of tabular/text tasks
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42))
    ])
    
    print(f"Started training model: {model_name}...")
    start_time = time.time()
    pipeline.fit(X_train, y_train)
    training_duration = time.time() - start_time
    print(f"Training completed in {training_duration:.2f}s")
    
    # 4. Evaluate
    y_pred = pipeline.predict(X_test)
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, zero_division=0))
    }
    
    print(f"Evaluation Metrics: {metrics}")
    
    # 5. Save artifacts
    version = f"v{int(time.time())}"
    artifact_rel_dir = f"ml/models/{model_name}/{version}"
    artifact_dir = os.path.join(PROJECT_ROOT, artifact_rel_dir)
    os.makedirs(artifact_dir, exist_ok=True)
    
    # Use relative path for artifact_location to keep it portable if root changes
    model_file_name = "model.pkl"
    model_path = os.path.join(artifact_dir, model_file_name)
    joblib.dump(pipeline, model_path)
    
    metadata = {
        "model_name": model_name,
        "version": version,
        "metrics": metrics,
        "features": list(X.columns),
        "dataset_source": os.path.basename(dataset_path),
        "training_duration": training_duration,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(os.path.join(artifact_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    return {
        "model_name": model_name,
        "version": version,
        "artifact_location": os.path.join(artifact_rel_dir, model_file_name),
        "metrics": metrics,
        "metadata": metadata
    }

def register_model_version(db_session, train_results):
    """
    Registers a newly trained model version in the database model registry.
    """
    from ..db_models import ModelVersion
    
    model_version = ModelVersion(
        model_name=train_results["model_name"],
        version=train_results["version"],
        accuracy=train_results["metrics"]["accuracy"],
        precision=train_results["metrics"]["precision"],
        recall=train_results["metrics"]["recall"],
        f1_score=train_results["metrics"]["f1_score"],
        artifact_location=train_results["artifact_location"],
        metadata_json=train_results["metadata"],
        is_active=False  # New models are not active by default
    )
    
    db_session.add(model_version)
    db_session.commit()
    db_session.refresh(model_version)
    
    print(f"Successfully registered model version {train_results['version']} (ID: {model_version.id})")
    return model_version.id

if __name__ == "__main__":
    # Integration test logic
    import argparse
    from ..db import SessionLocal

    parser = argparse.ArgumentParser(description="Train Phishing Detection Model")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the parquet dataset")
    parser.add_argument("--name", type=str, default="ensemble", help="Model name")
    
    args = parser.parse_args()
    
    results = train_and_evaluate(args.dataset, args.name)
    if results:
        db = SessionLocal()
        register_model_version(db, results)
        db.close()
