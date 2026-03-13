import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_curve, auc
import matplotlib.pyplot as plt
from joblib import load
from app.features import extract_features


SAMPLE_PATH = os.environ.get("SAMPLE_PATH", "backend/sample_data/sample.csv")
MODEL_PATH = os.environ.get("MODEL_PATH", "backend/models/model.joblib")


def main():
    df = pd.read_csv(SAMPLE_PATH)
    X_list = []
    y_list = []
    for _, row in df.iterrows():
        X_list.append(extract_features(row["url"], row.get("html", None)))
        y_list.append(1 if row["label"] == "phishing" else 0)
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    pipe = load(MODEL_PATH)
    y_pred = pipe.predict(X)
    y_proba = pipe.predict_proba(X)[:, 1]
    report = classification_report(y, y_pred, output_dict=True, zero_division=0)
    with open(os.path.join(os.path.dirname(MODEL_PATH), "classification_report.json"), "w") as f:
        json.dump(report, f)
    fpr, tpr, _ = roc_curve(y, y_proba)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr, label=f"ROC curve (area = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("FPR")
    plt.ylabel("TPR")
    plt.title("ROC AUC")
    out_path = os.path.join(os.path.dirname(MODEL_PATH), "roc_auc.png")
    plt.savefig(out_path)


if __name__ == "__main__":
    main()