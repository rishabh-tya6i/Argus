import os
import json
import logging
import time
import traceback
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
from .schemas import PredictResponse, Explanation, ModelScores, ExplanationReason
from .heuristics import generate_heuristic_reasons
from .services.domain_intel import evaluate_domain_for_url
from .services.visual_similarity import visual_similarity_engine
from .observability import (
    tracer,
    get_correlation_ctx,
    MODEL_INFERENCE_LATENCY,
    VISUAL_IMPERSONATION_HITS_TOTAL,
)

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

logger = logging.getLogger(__name__)


class EnsembleModel:
    def __init__(self):
        self.classical_pipeline: Optional[Pipeline] = None

        # Initialize Deep Learning Models
        self.url_detector = URLDetector(model_path=os.environ.get("URL_MODEL_PATH"))
        self.html_detector = HTMLDetector(model_path=os.environ.get("HTML_MODEL_PATH"))
        self.visual_detector = VisualDetector(model_path=os.environ.get("VISUAL_MODEL_PATH"))

        self.fusion_model = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache = {}  # Simple in-memory cache for demo

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

    def _timed_predict(self, detector_name: str, fn, *args) -> float:
        """Run a detector function, record latency metric, and return probability."""
        start = time.perf_counter()
        try:
            result = fn(*args)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            MODEL_INFERENCE_LATENCY.labels(detector=detector_name).observe(elapsed)
            logger.error(
                f"Model inference error in {detector_name}",
                extra={
                    **get_correlation_ctx(),
                    "event": "model_inference_error",
                    "detector": detector_name,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            return 0.5  # safe default on failure
        elapsed = time.perf_counter() - start
        MODEL_INFERENCE_LATENCY.labels(detector=detector_name).observe(elapsed)
        return float(result)

    async def predict(
        self,
        url: str,
        html: Optional[str],
        screenshot: Optional[str],
        db: Optional["Session"] = None,  # type: ignore[name-defined]
    ) -> PredictResponse:
        # Check cache (URL only for simplicity)
        if url in self.cache:
            return self.cache[url]

        loop = asyncio.get_running_loop()
        ctx = get_correlation_ctx()

        with tracer.start_as_current_span("model.predict") as span:
            span.set_attribute("url", url)
            for k, v in ctx.items():
                span.set_attribute(k, v)

            # --- URL Feature Extraction span ---
            with tracer.start_as_current_span("model.url_feature_extraction"):
                future_classical = loop.run_in_executor(
                    self.executor, self._timed_predict, "classical", self._predict_classical, url, html
                )
                future_url = loop.run_in_executor(
                    self.executor, self._timed_predict, "url", self.url_detector.predict, url
                )

            # --- HTML Analysis span ---
            with tracer.start_as_current_span("model.html_analysis"):
                future_html = loop.run_in_executor(
                    self.executor, self._timed_predict, "html", self.html_detector.predict, html
                )

            # --- Visual Impersonation Detection span ---
            with tracer.start_as_current_span("model.visual_impersonation_detection"):
                future_visual = loop.run_in_executor(
                    self.executor, self._timed_predict, "visual", self.visual_detector.predict, screenshot
                )

            # Wait for all to complete
            prob_classical, prob_url, prob_html, prob_visual = await asyncio.gather(
                future_classical, future_url, future_html, future_visual
            )

            # 5. Ensemble Fusion (Simple Weighted Average for now)
            base_score = (
                (prob_classical * 0.3)
                + (prob_url * 0.3)
                + (prob_html * 0.2)
                + (prob_visual * 0.2)
            )

            # 6. Domain reputation / threat intelligence enrichment.
            domain_risk_score = 0.0
            domain_reasons = []
            if db is not None:
                try:
                    _domain, domain_risk_score, domain_reasons = evaluate_domain_for_url(db, url)
                except Exception:
                    domain_risk_score = 0.0
                    domain_reasons = []

            final_score = base_score
            if domain_risk_score > 0:
                final_score = max(0.0, min(1.0, 0.85 * base_score + 0.15 * domain_risk_score))

            important_features: List[str] = []
            heuristic_reasons = generate_heuristic_reasons(url, html)
            heuristic_reasons.extend(domain_reasons)

            # Ensure Visual Similarity cache is loaded
            if db is not None and not visual_similarity_engine.cached_brands:
                visual_similarity_engine.load_cache(db)

            # 7. Escalated Visual Brand Impersonation check
            if final_score > 0.4 and screenshot:
                features_df = extract_features(url, html)
                has_login_form = features_df["form_count"].iloc[0] > 0 or features_df["input_count"].iloc[0] > 0

                if has_login_form:
                    future_impersonation = loop.run_in_executor(
                        self.executor, visual_similarity_engine.detect_impersonation, screenshot, url
                    )
                    is_impersonation, impersonation_details = await future_impersonation

                    if is_impersonation and impersonation_details:
                        brand_name = impersonation_details["brand_name"]
                        sim_score = impersonation_details["similarity_score"]

                        # Boost final score significantly
                        final_score = min(1.0, final_score + 0.3)
                        VISUAL_IMPERSONATION_HITS_TOTAL.inc()

                        reason = ExplanationReason(
                            code="BRAND_IMPERSONATION_DETECTED",
                            category="visual_similarity",
                            weight=0.9,
                            message=f"Page visually resembles {brand_name} login page but is hosted on an unrelated domain. "
                                    f"(Similarity: {sim_score})"
                        )
                        heuristic_reasons.append(reason)
                        important_features.append(f"Strong visual similarity to {brand_name}")

            prediction = "phishing" if final_score > 0.5 else "safe"

            span.set_attribute("prediction", prediction)
            span.set_attribute("confidence", round(final_score, 4))

            # Identify important features from model scores
            if prob_url > 0.7:
                important_features.append("Suspicious URL semantics (Transformer URL model)")
            if prob_html > 0.7:
                important_features.append("Malicious HTML structure (HTML content model)")
            if prob_visual > 0.7:
                important_features.append("Visual similarity to known phishing layouts (screenshot model)")
            if prob_classical > 0.7:
                important_features.append("Classical URL/HTML feature patterns consistent with phishing")

            for reason in heuristic_reasons[:3]:
                if not reason.code == "BRAND_IMPERSONATION_DETECTED":
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
        if len(self.cache) > 1000:  # Simple eviction
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
