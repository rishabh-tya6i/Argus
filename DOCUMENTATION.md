# Argus Platform Documentation

Welcome to the official developer documentation for **Argus**, a production-grade, enterprise-ready phishing detection ecosystem. Argus provides multi-layered security analysis across web, email, and browser environments.

---

## 🚀 1. Project Overview

### What is Argus?
Argus is an advanced cybersecurity platform designed to protect organizations from phishing and credential harvesting attacks. It integrates multiple detection technologies—Machine Learning, Heuristic Rule Engines, and Real-time Threat Intelligence—into a unified, multi-tenant backend.

### Key Features
*   **Hybrid Detection Stack**: Parallel execution of ML (XGBoost), rule-based checks, and threat intel lookups.
*   **Native Integrations**:
    *   **Gmail**: Passive email scanning and URL extraction.
    *   **Chrome Extension**: Real-time browser protection and DevTools security inspection.
*   **Analyst-First Dashboard**: Deep-dive investigation views, real-time WebSocket feeds, and alert management.
*   **Closed-Loop ML Pipeline**: Automated dataset collection from human feedback and seamless model retraining.
*   **Enterprise Infrastructure**: Kubernetes-ready, multi-tenant architecture with Prometheus/Grafana observability.

---

## 🏗️ 2. System Architecture

Argus is built on a distributed microservices model centered around a modular **FastAPI** backend.

### Architecture Overview
1.  **Backend (FastAPI)**: Modular routers for `auth`, `scans`, `alerts`, `models`, and `tenants`. Uses SQLAlchemy as an ORM with support for SQLite and PostgreSQL.
2.  **ML Pipeline**: A dedicated service for feature extraction, training, and model versioning.
3.  **Detection Engine**:
    *   **Rule Engine**: Implements fast heuristics for known phishing patterns.
    *   **ML Predictor**: Uses an ensemble of XGBoost models analyzing URL structure and HTML content.
    *   **Threat Intel**: Connects to external reputation feeds.
4.  **Frontend (React)**: High-performance dashboard built with Vite and Tailwind CSS.
5.  **Chrome Extension**: MV3-compliant extension using background scripts for passive monitoring and a custom DevTools panel for active analysis.
6.  **Workers & Queues**: Background jobs managed via Redis for resource-heavy tasks like the browser sandbox and external threat log processing.

### Data Flow Diagram (Textual)
> `User Input (URL/Email)` → `API Sanitization` → `Feature Extraction` → `Ensemble Inference` → `Decision Aggregate` → `Alert Generation` → `WebSocket Broadcast` → `Analyst Dashboard`.

---

## 📥 3. Installation Guide

### Prerequisites
*   **Python**: 3.10+
*   **Node.js**: 18+ (LTS recommended)
*   **Docker**: Required for local container stack or Kubernetes.

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m backend.app.db init  # Initialize database schema
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Chrome Extension Setup
1.  Navigate to `chrome://extensions/`.
2.  Enable **Developer Mode**.
3.  Click **Load Unpacked** and select the `extension/` directory.

---

## 🔑 4. Environment Variables

Create a `.env` in the root of your backend project.

| Variable | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Yes | `sqlite:///./phishguard.db` | Primary DB connection string. |
| `JWT_SECRET` | Yes | `change-me-in-production` | Secret for signing JWT tokens. |
| `API_PORT` | No | `8000` | Port for the backend API. |
| `REDIS_URL` | No | `redis://localhost:6379` | Background job queue. |
| `MODEL_PATH` | No | `backend/models/model.joblib` | Path to production model artifact. |

---

## 🛡️ 5. How to Use Argus

### A. Manual URL Scan
Submit URLs to the `/api/predict` endpoint. The platform returns a structured response including a high-level verdict and detailed feature-level explanations.

### B. Gmail Integration
Connect your workspace via the **Gmail Scans** page. Argus will passively monitor unread emails, extract links, and populate the Dashboard with detection results.

### C. Chrome Extension
*   **Real-time Protection**: Notifies users instantly if an active tab is flagged.
*   **Security Panel**: Press `F12` > `Argus Security` to view a real-time extraction of DOM metadata, script entropy, and form attributes.

### D. Dashboard
*   **Scan Feed**: Live list of all system-wide scans.
*   **Investigation View**: Deep-dive into a specific scan, showing screenshots and detection reasoning.
*   **Feedback Submission**: Analysts can correct detections, which automatically populates the ML training queue.

---

## 🧪 6. ML Pipeline Guide

### A. Dataset Flow
When an analyst submits feedback (e.g., "This was a false positive"), a new entry is added to the `TrainingDataset` table. This entry links the original `Scan` features with the corrected `FeedbackLabel`.

### B. Feature Engineering
Argus extracts over 50 features per URL, including:
*   **Structural**: Length, subdomains, TLD reputation, punycode.
*   **Topical**: Phishing keywords (e.g., "paypal", "login", "otp").
*   **HTML**: Input field count, hidden forms, external script ratios.

### C. Training Models
Run the training script to produce new model versions:
```bash
python -m app.ml.train
```

### D. Model Versioning & Retraining
*   Models are versioned logically in the `ModelVersion` table.
*   Argus supports **Shadow Mode**, allowing you to deploy new models for monitoring without letting them affect live user traffic.
*   **Retraining**: Automatic retraining can be triggered via CLI or API once a threshold of new feedback samples (e.g., 500) is reached.

---

## 🔍 7. Detection Engine Explanation

Argus uses a **Decision Aggregation Strategy**:
1.  **Phase 1: Heuristics**: Immediate blocking if matching known malicious patterns.
2.  **Phase 2: ML Inference**: The XGBoost model calculates a probability score [0-1].
3.  **Phase 3: Intelligence Cross-Check**: Checks against internal and external threat feeds.
4.  **Final Verdict Calculation**:
    - **Safe**: If Confidence < 0.5.
    - **Suspicious**: If 0.5 ≤ Confidence < 0.85 (triggers sandbox analysis).
    - **Phishing**: If Confidence ≥ 0.85 OR any critical rule match.

---

## 🧬 8. API Documentation

### POST `/api/predict`
Request a real-time scan.

**Request Body:**
```json
{
  "url": "http://paypal-security-update.com",
  "html": "<html>...</html>",
  "source": "chrome_extension"
}
```

**Successful Response (200 OK):**
```json
{
  "prediction": "phishing",
  "confidence": 0.98,
  "explanation": {
    "important_features": ["has_brand_name", "ip_in_url", "mismatched_domain"],
    "reasons": [{"code": "BRAND_REPUTATION", "weight": 0.8, "message": "High-risk domain pretending to be PayPal"}]
  }
}
```

---

## ⚡ 9. Real-Time System (WebSockets)

Argus utilizes WebSockets for sub-second updates.
*   **Connector**: `manager = ConnectionManager()` in `main.py`.
*   **Broadcasting**: Every time a scan is persisted, an event is broadcast to all active dashboard subscribers via `/ws/scans`.

---

## 🐳 10. Deployment Guide

### Local Development
Follow the **Installation Guide** section using `uvicorn` and `npm run dev`.

### Docker Setup
Use the provided `docker-compose.yml`:
```bash
docker-compose up --build
```

### Kubernetes Overview
Argus is k8s-native. Use `./scripts/k8s_deploy.sh` to spin up the full infrastructure, including:
*   FastAPI HPA (Horizontal Pod Autoscalers).
*   StatefulSet for PostgreSQL.
*   Prometheus/Grafana for full-stack monitoring.

---

## 🛠️ 11. Troubleshooting

*   **"Model Not Found" Error**: Ensure you have run the training script or placed a valid `model.joblib` in the `backend/models/` directory.
*   **Websocket Disconnection**: Ensure your firewall/proxy allows Long-polling and WebSocket upgrades.
*   **Database Locked**: If using SQLite locally, ensure no other processes are locking the `.db` file during concurrent scans.

---

## 🤝 12. Contribution Guide

We follow a modular PR process.
1.  **Detectors**: Add new logic to `app/detectors/`.
2.  **Scanners**: Add new browser-based scanning modules in `app/security_scanner/`.
3.  **UI**: Follow Atomic Design principles in `frontend/src/components/`.

---

## 🗺️ 13. Future Roadmap

*   **Zero-Day Fingerprinting**: Automated creation of blocklist rules from recurring ML patterns.
*   **Screenshot-to-Embedding**: Vector-based visual analysis for brand impersonation.
*   **Enterprise Integrations**: Slack, PagerDuty, and SIEM (Splunk/Sentinel) exporters.

---

*Argus Security Research Lab © 2026. Powering the frontlines of web security.*
