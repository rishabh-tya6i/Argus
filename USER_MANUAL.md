# User Manual: Multi-Modal Zero-Day Phishing Detection System

## 1. Introduction
This system provides real-time protection against phishing attacks using a multi-modal AI approach. It analyzes URLs, HTML content, and visual screenshots to detect zero-day threats that traditional blocklists miss.

## 2. Installation Guide

### Prerequisites
-   Python 3.9+
-   Node.js 18+
-   Google Chrome or Microsoft Edge

### A. Backend Setup
1.  Navigate to the project root:
    ```bash
    cd Phishing-Link-Detector
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r backend/requirements.txt
    ```
4.  Start the API server:
    ```bash
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ```
    *The server will start on http://localhost:8000*

### B. Frontend Dashboard Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the dashboard:
    ```bash
    npm run dev
    ```
    *Access the dashboard at http://localhost:5173*

### C. Browser Extension Setup
1.  Open Chrome and go to `chrome://extensions`.
2.  Enable **Developer mode** (top right toggle).
3.  Click **Load unpacked**.
4.  Select the `extension` folder inside the project directory.
5.  The "Zero-Day Phishing Detector" icon should appear in your toolbar.

## 3. Usage Guide

### Using the Extension
-   **Automatic Protection**: Just browse the web as usual. The extension monitors every page load.
-   **Safe Sites**: The extension icon badge will show "OK" (Green).
-   **Phishing Sites**:
    -   A full-screen **Red Warning Overlay** will block the page.
    -   The extension icon badge will show "!" (Red).
    -   **To Proceed**: Click "Proceed Anyway" on the overlay (use with caution!).
    -   **False Positive**: Click "Report as Safe" on the overlay to send feedback.

### Using the Dashboard
-   **Live Feed**: View real-time detections from your browser extension.
-   **Manual Analysis**: Paste a URL (and optional HTML) into the "Analyze URL" box to manually trigger a scan.
-   **Detailed Reports**: Click on a result to see the breakdown of scores from the URL, HTML, and Visual models.

## 4. Troubleshooting
-   **Extension Error**: "Error connecting to server"
    -   Ensure the Backend API is running on port 8000.
-   **Slow Analysis**:
    -   The first request might be slow as models load into memory. Subsequent requests are cached.
-   **False Positives**:
    -   The current models are trained on small demo datasets. For production use, retrain using the scripts in `backend/train/`.
