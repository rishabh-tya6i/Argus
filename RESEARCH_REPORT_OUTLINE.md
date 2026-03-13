# Research Report Outline
## Title: A Multi-Modal, Zero-Day Phishing Detection System using Transformer-Based URL Analysis, HTML Inspection, and Visual Classification

### Abstract
-   Brief summary of the rising threat of zero-day phishing.
-   Introduction of the proposed multi-modal system.
-   Key results (e.g., "Achieved X% accuracy on zero-day samples").

### 1. Introduction
-   **1.1 Background**: The evolution of phishing from simple spam to sophisticated clones.
-   **1.2 Problem Statement**: Inadequacy of static blocklists and single-modal detection against obfuscated/zero-day attacks.
-   **1.3 Objectives**: Develop a real-time, client-side protection system using ensemble deep learning.

### 2. Literature Review
-   **2.1 URL-Based Detection**: Review of lexical analysis and recent Transformer (BERT) approaches.
-   **2.2 Content-Based Detection**: Analysis of HTML structural features (TF-IDF, DOM trees).
-   **2.3 Visual Phishing Detection**: Overview of computer vision techniques (SIFT, CNNs, Visual Transformers) for screenshot analysis.
-   **2.4 Gap Analysis**: Lack of integrated, real-time multi-modal systems in browser extensions.

### 3. Methodology (System Architecture)
-   **3.1 Overview**: High-level diagram of the Extension-Backend-Dashboard architecture.
-   **3.2 Data Collection**:
    -   Sources: PhishTank, OpenPhish, Alexa Top 1M.
    -   Preprocessing: Screenshot capture, HTML parsing, URL tokenization.
-   **3.3 Model Architecture**:
    -   **Model A (URL)**: DistilBERT for semantic URL analysis.
    -   **Model B (HTML)**: 1D-CNN/LSTM for structural tag analysis.
    -   **Model C (Visual)**: EfficientNet-B0 for image classification of page screenshots.
    -   **Model D (Classical)**: XGBoost on handcrafted features (WHOIS, length, etc.).
-   **3.4 Ensemble Fusion**:
    -   Weighted averaging / Stacking meta-classifier logic.
-   **3.5 Real-Time Inference**:
    -   Asyncio pipeline and caching strategies for <300ms latency.

### 4. Implementation
-   **4.1 Backend**: FastAPI, PyTorch, Scikit-learn.
-   **4.2 Browser Extension**: Manifest V3, Chrome Scripting API.
-   **4.3 Hardware Setup**: Training environment (GPU specs).

### 5. Results and Evaluation
-   **5.1 Metrics**: Accuracy, Precision, Recall, F1-Score, Latency.
-   **5.2 Comparative Analysis**: Proposed System vs. Google Safe Browsing (simulated) vs. Single-Modal models.
-   **5.3 Ablation Study**: Contribution of each model (URL vs. Visual vs. HTML).
-   **5.4 Case Studies**: Examples of zero-day sites detected successfully.

### 6. Conclusion and Future Work
-   **6.1 Conclusion**: Summary of contributions.
-   **6.2 Limitations**: Resource consumption, adversarial attacks on ML.
-   **6.3 Future Work**: Federated learning, on-device inference (WebGPU).

### References
-   [List of IEEE/ACM papers cited]
