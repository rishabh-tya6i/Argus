# Argus

<p align="center">
  <img src="https://img.shields.io/badge/Argus-Cybersecurity%20Platform-0A192F?style=for-the-badge&logo=shield&logoColor=white" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Detection-Hybrid%20AI-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Latency-<300ms-success?style=flat-square" />
  <img src="https://img.shields.io/badge/Architecture-Distributed-informational?style=flat-square" />
  <img src="https://img.shields.io/badge/Deployment-Kubernetes-blue?style=flat-square" />
</p>

---

## Overview

Argus is an intelligent phishing detection and web security analysis platform designed to identify malicious websites using a **multi-layer hybrid detection system**.

It combines:

* Machine Learning inference
* Rule-based heuristics
* Threat intelligence
* Dynamic sandbox execution

to deliver **high-confidence, explainable phishing detection** in real time.

---

## Core System (High-Level)

```mermaid
flowchart LR
A[Input URL / Email] --> B[Detection Orchestrator]
B --> C[ML Model]
B --> D[Rule Engine]
B --> E[Threat Intelligence]
C --> F[Hybrid Scoring]
D --> F
E --> F
F --> G[Explainable Result]
```

---

## Platform Capabilities

### Detection Engine

* Hybrid scoring (ML + Rules + Threat Intel)
* URL entropy and pattern analysis
* Credential harvesting detection
* Redirect chain tracking
* JavaScript behavior inspection

---

### Visual Impersonation Detection

* Screenshot-based similarity analysis
* Detects phishing clones of major platforms:

  * Google
  * Microsoft
  * AWS
  * PayPal
  * Apple
  * GitHub

---

### Threat Intelligence

* Newly registered domain detection
* Typosquatting analysis
* Homograph attack detection
* Certificate transparency monitoring
* External threat feed ingestion

---

### Sandbox Analysis

```mermaid
sequenceDiagram
User->>API: Submit URL
API->>Queue: Create job
Worker->>Browser: Launch sandbox
Browser->>Website: Execute page
Website-->>Worker: Behavior signals
Worker->>DB: Store artifacts
Worker->>API: Return results
```

* Headless Chromium execution
* Network and redirect tracking
* DOM mutation analysis
* Credential interaction monitoring

---

## System Architecture

```mermaid
graph TD

Client[Client / Extension / Gmail] --> API[Argus API]

API --> Orchestrator[Detection Engine]

Orchestrator --> ML[ML Model]
Orchestrator --> Rules[Rule Engine]
Orchestrator --> Intel[Threat Intel]

API --> Queue[Redis Queue]

Queue --> Sandbox[Sandbox Worker]
Queue --> Scanner[Security Worker]

Sandbox --> DB[(PostgreSQL)]
Scanner --> DB

API --> Metrics[Prometheus]
Metrics --> Grafana[Grafana]
```

---

## Tech Stack

### Backend

![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-orange)
![Redis](https://img.shields.io/badge/Queue-Redis-red)

### ML & Analysis

![XGBoost](https://img.shields.io/badge/ML-XGBoost-blue)
![Playwright](https://img.shields.io/badge/Sandbox-Playwright-black)
![Chromium](https://img.shields.io/badge/Browser-Chromium-lightgrey)

### Infrastructure

![Docker](https://img.shields.io/badge/Docker-Container-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Orchestration-blue)
![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-orange)
![Grafana](https://img.shields.io/badge/Visualization-Grafana-yellow)

---

## Detection Pipeline

```mermaid
flowchart LR
A[Incoming URL]
--> B[URL Analysis]
--> C[HTML Inspection]
--> D[Sandbox Execution]
--> E[Threat Intelligence]
--> F[Hybrid Risk Score]
```

---

## Project Structure

```
backend/
  app/
    detection/
    ml/
    services/
    workers/

frontend/
  src/

extension/
  chrome-extension/

cli/
  scanphish.py

deploy/
  k8s/

monitoring/
  prometheus.yml
  grafana_dashboard.json
```

---

## Local Development

### Requirements

* Python 3.11
* Docker
* Node.js

### Run Locally

```bash
./scripts/dev_up.sh
```

Access:

* API → http://localhost:8000
* Grafana → http://localhost:3000
* Prometheus → http://localhost:9090

---

## Kubernetes Deployment

```bash
./scripts/k8s_deploy.sh
```

Includes:

* API services
* Workers
* Redis
* PostgreSQL
* Monitoring stack

---

## CLI Scanner

```bash
python cli/scanphish.py https://example.com
```

Returns:

* phishing verdict
* risk score
* detection explanation
* intelligence signals

---

## Observability

Metrics endpoint:

```
/metrics
```

Tracked metrics:

* request throughput
* detection rates
* worker health
* model latency

---

## Security Model

* tenant isolation
* sandbox isolation
* non-root containers
* structured logging
* rate limiting
* authentication

---

## Roadmap

* advanced ML model tuning
* enterprise SSO
* SIEM integrations
* alerting pipelines
* extended threat feeds

---

## License

Research and educational use. Licensing may evolve for production deployment.

---

<p align="center">
  <img src="https://img.shields.io/badge/Argus-Building%20Adaptive%20Security-0A192F?style=for-the-badge&logo=shield&logoColor=white" />
</p>
