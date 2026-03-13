# System Architecture: Multi-Modal Zero-Day Phishing Detection System

## 1. Overview
This system is a next-generation phishing detection framework designed to detect zero-day phishing URLs, obfuscated links, and malicious web content in real-time. It leverages a multi-modal approach combining URL analysis, HTML inspection, visual screenshot classification, and classical feature extraction, fused by an ensemble model.

## 2. High-Level Architecture
The system consists of three main components:
1.  **Browser Extension (Client)**: Monitors user navigation, captures page content/screenshots, and blocks threats.
2.  **Backend API (Server)**: Orchestrates the multi-modal analysis and ensemble decision-making.
3.  **Admin Dashboard (Web UI)**: Provides real-time monitoring, analytics, and model management.

## 3. Component Details

### 3.1. Browser Extension
-   **Platform**: Chrome/Edge (Manifest V3)
-   **Responsibilities**:
    -   Intercept navigation events.
    -   Send URL to Backend API for analysis.
    -   (Optional) Capture DOM/HTML and Screenshot if required by the backend.
    -   Display warning/blocking overlay for malicious sites.
    -   Allow user reporting.

### 3.2. Backend API
-   **Framework**: FastAPI (Python)
-   **Responsibilities**:
    -   **API Layer**: Handle requests from extension and dashboard.
    -   **Data Collection**: Fetch HTML and capture screenshots (headless browser) if not provided by client.
    -   **Model Inference**: Run 4 parallel models.
    -   **Ensemble**: Combine predictions.
    -   **Database**: Store logs, feedback, and model metrics.

### 3.3. Multi-Modal Detection Engine (The Core)
The engine runs 4 parallel analysis pipelines:

#### A. URL Transformer Model
-   **Input**: Raw URL string.
-   **Model**: DistilBERT / BERT (fine-tuned).
-   **Features**: Character-level embeddings, semantic tokens.
-   **Output**: Probability (0-1).

#### B. HTML Code Analysis Model
-   **Input**: Raw HTML content.
-   **Model**: CNN or LSTM.
-   **Features**: Structural tags, script density, hidden iframes, forms.
-   **Output**: Probability (0-1).

#### C. Screenshot-Based Visual Classifier
-   **Input**: Page Screenshot (Image).
-   **Model**: EfficientNet / MobileNet / ViT.
-   **Features**: Visual layout, logo impersonation, login form detection.
-   **Output**: Probability (0-1).

#### D. Classical Feature-Based Model
-   **Input**: Extracted Features (URL length, dot count, WHOIS age, etc.).
-   **Model**: XGBoost / RandomForest.
-   **Output**: Probability (0-1).

#### E. Ensemble Fusion Layer
-   **Input**: Outputs from A, B, C, D.
-   **Model**: Logistic Regression / MLP.
-   **Output**: Final Phishing Score + Label (Safe/Suspicious/Phishing).

### 3.4. Admin Dashboard
-   **Framework**: React / Next.js.
-   **Features**:
    -   Live threat feed.
    -   Model performance metrics (Accuracy, F1, etc.).
    -   Visual analysis results (screenshots of detected sites).
    -   System health monitoring.

## 4. Data Flow
1.  **User visits URL**.
2.  **Extension** sends URL to **Backend**.
3.  **Backend** checks cache/allowlist.
4.  If new/suspicious:
    -   **Backend** fetches HTML & Screenshot (Headless Chrome).
    -   **Models** A, B, C, D run in parallel.
    -   **Ensemble** aggregates scores.
5.  **Backend** returns verdict to **Extension**.
6.  **Extension** blocks page if Phishing.
7.  **Dashboard** updates with new event.

## 5. Technology Stack
-   **Backend**: Python, FastAPI, PyTorch/TensorFlow, Scikit-learn, Transformers, Playwright/Puppeteer.
-   **Frontend**: React, TailwindCSS, Chart.js/Recharts.
-   **Extension**: JavaScript/TypeScript, HTML/CSS.
-   **Database**: PostgreSQL / MongoDB (for logging).
-   **Deployment**: Docker, Kubernetes (optional).
