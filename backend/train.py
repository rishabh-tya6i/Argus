import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from joblib import dump
from app.features import extract_features
from app.model import build_pipeline


SAMPLE_PATH = os.environ.get("SAMPLE_PATH", "backend/sample_data/sample.csv")
MODEL_PATH = os.environ.get("MODEL_PATH", "backend/models/model.joblib")


def load_and_featurize(path: str) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(path)
    X_list = []
    y_list = []
    for _, row in df.iterrows():
        X_list.append(extract_features(row["url"], row.get("html", None)))
        y_list.append(1 if row["label"] == "phishing" else 0)
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    return X, y


def main():
    X, y = load_and_featurize(SAMPLE_PATH)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42)
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
    }
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    dump(pipe, MODEL_PATH)
    with open(os.path.join(os.path.dirname(MODEL_PATH), "metrics.json"), "w") as f:
        json.dump(metrics, f)


if __name__ == "__main__":
    main()