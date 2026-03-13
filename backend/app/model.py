import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

from .features import extract_features
from .schemas import PredictResponse, Explanation, ModelScores
from .heuristics import generate_heuristic_reasons

# --- Configuration ---
MODEL_PATH = os.environ.get("MODEL_PATH", "backend/models/model.joblib")
SAMPLE_PATH = os.environ.get("SAMPLE_PATH", "backend/sample_data/sample.csv")

NUMERIC_FEATURES = [
    "length",
    "count_dots",
    "count_hyphens",
    "has_ip",
    "ratio_digits",
    "presence_of_https",
    "count_query_params",
    "domain_tokens_entropy",
    "form_count",
    "input_count",
]

from .detectors import URLDetector, HTMLDetector, VisualDetector

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

class EnsembleModel:
    def __init__(self):
        self.classical_pipeline: Optional[Pipeline] = None
        
        # Initialize Deep Learning Models
        self.url_detector = URLDetector(model_path=os.environ.get("URL_MODEL_PATH"))
        self.html_detector = HTMLDetector(model_path=os.environ.get("HTML_MODEL_PATH"))
        self.visual_detector = VisualDetector(model_path=os.environ.get("VISUAL_MODEL_PATH"))
        
        self.fusion_model = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache = {} # Simple in-memory cache for demo

    def load_or_train_classical(self, model_path: str, sample_path: str):
        """Loads the classical ML pipeline or trains a simple one if missing."""
        if os.path.exists(model_path):
            self.classical_pipeline = joblib.load(model_path)
            print(f"Loaded classical model from {model_path}")
        else:
            print("Training classical model from sample data...")
            self._train_classical(model_path, sample_path)

    def _train_classical(self, model_path: str, sample_path: str):
        if not os.path.exists(sample_path):
            # Create dummy data if sample doesn't exist
            df = pd.DataFrame([
                {"url": "http://google.com", "html": "<html></html>", "label": "legitimate"},
                {"url": "http://evil-login.com", "html": "<form>login</form>", "label": "phishing"}
            ])
        else:
            df = pd.read_csv(sample_path)

        X_list = []
        y_list = []
        for _, row in df.iterrows():
            f = extract_features(row["url"], row.get("html", ""))
            X_list.append(f)
            y_list.append(1 if row["label"] == "phishing" else 0)
        
        X = pd.concat(X_list, ignore_index=True)
        y = np.array(y_list)

        preprocess = ColumnTransformer(
            transformers=[
                ("text", TfidfVectorizer(max_features=500), "html_text"),
                ("cat", OneHotEncoder(handle_unknown="ignore"), ["tld"]),
                ("num", "passthrough", NUMERIC_FEATURES),
            ],
            remainder="drop",
        )
        clf = LogisticRegression(max_iter=500)
        pipe = Pipeline(steps=[("preprocess", preprocess), ("clf", clf)])
        pipe.fit(X, y)
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(pipe, model_path)
        self.classical_pipeline = pipe
        print("Classical model trained and saved.")

    async def predict(self, url: str, html: Optional[str], screenshot: Optional[str]) -> PredictResponse:
        # Check cache (URL only for simplicity)
        if url in self.cache:
            return self.cache[url]

        loop = asyncio.get_running_loop()

        # 1. Run all models in parallel using ThreadPoolExecutor
        # We use run_in_executor because PyTorch/Sklearn are CPU bound and blocking
        
        future_classical = loop.run_in_executor(self.executor, self._predict_classical, url, html)
        future_url = loop.run_in_executor(self.executor, self.url_detector.predict, url)
        future_html = loop.run_in_executor(self.executor, self.html_detector.predict, html)
        future_visual = loop.run_in_executor(self.executor, self.visual_detector.predict, screenshot)

        # Wait for all to complete
        prob_classical, prob_url, prob_html, prob_visual = await asyncio.gather(
            future_classical, future_url, future_html, future_visual
        )

        # 5. Ensemble Fusion (Simple Weighted Average for now)
        # Weights: Classical=0.3, URL=0.3, HTML=0.2, Visual=0.2
        final_score = (
            (prob_classical * 0.3) +
            (prob_url * 0.3) +
            (prob_html * 0.2) +
            (prob_visual * 0.2)
        )

        prediction = "phishing" if final_score > 0.5 else "safe"

        # Identify important features from model scores
        important_features: List[str] = []
        if prob_url > 0.7:
            important_features.append("Suspicious URL semantics (Transformer URL model)")
        if prob_html > 0.7:
            important_features.append("Malicious HTML structure (HTML content model)")
        if prob_visual > 0.7:
            important_features.append("Visual similarity to known phishing layouts (screenshot model)")
        if prob_classical > 0.7:
            important_features.append("Classical URL/HTML feature patterns consistent with phishing")

        # Heuristic, rule-based explanations (hidden forms, redirects, obfuscated JS, etc.)
        heuristic_reasons = generate_heuristic_reasons(url, html)
        # Also surface top heuristic messages as human-readable important features
        for reason in heuristic_reasons[:3]:
            important_features.append(reason.message)

        response = PredictResponse(
            prediction=prediction,
            confidence=round(final_score, 4),
            explanation=Explanation(
                model_scores=ModelScores(
                    url_model=round(prob_url, 4),
                    html_model=round(prob_html, 4),
                    visual_model=round(prob_visual, 4),
                    classical_model=round(prob_classical, 4)
                ),
                important_features=important_features,
                reasons=heuristic_reasons,
            )
        )
        
        # Update cache
        self.cache[url] = response
        if len(self.cache) > 1000: # Simple eviction
            self.cache.pop(next(iter(self.cache)))
            
        return response

    def _predict_classical(self, url: str, html: Optional[str]) -> float:
        features_df = extract_features(url, html)
        if self.classical_pipeline:
            return float(self.classical_pipeline.predict_proba(features_df)[0][1])
        return 0.5

# Global instance
model_instance = EnsembleModel()

def ensure_model(model_path: str = MODEL_PATH, sample_path: str = SAMPLE_PATH) -> EnsembleModel:
    model_instance.load_or_train_classical(model_path, sample_path)
    return model_instance
