# Argus Deployment Guide

> **Platform:** Argus Phishing Detection Platform  
> **Version:** 2.0  
> **Last updated:** March 2026

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local Development with Docker Compose](#local-development-with-docker-compose)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Environment Variables Reference](#environment-variables-reference)
6. [Scaling Workers](#scaling-workers)
7. [Monitoring & Metrics](#monitoring--metrics)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│               Argus Platform                │
│                                             │
│  ┌────────────┐    ┌──────────────────────┐ │
│  │ argus-api  │───▶│ argus-sandbox-worker │ │
│  │ (FastAPI)  │    │ (Playwright/Chromium) │ │
│  └─────┬──────┘    └──────────────────────┘ │
│        │           ┌──────────────────────┐ │
│        ├──────────▶│ argus-threat-worker  │ │
│        │           │ (CT logs / NRD)      │ │
│        │           └──────────────────────┘ │
│        │           ┌──────────────────────┐ │
│        └──────────▶│argus-security-worker │ │
│                    │ (dynamic scanning)   │ │
│                    └──────────────────────┘ │
│                                             │
│  ┌──────────┐  ┌──────────┐                 │
│  │PostgreSQL│  │  Redis   │  (shared state) │
│  └──────────┘  └──────────┘                 │
│                                             │
│  ┌────────────┐  ┌─────────┐                │
│  │ Prometheus │  │ Grafana │  (observability)│
│  └────────────┘  └─────────┘                │
└─────────────────────────────────────────────┘
```

### Component Responsibilities

| Service | Image | Port | Role |
|---|---|---|---|
| `argus-api` | `argus-api` | 8000 | FastAPI, REST API, detection, metrics |
| `argus-sandbox-worker` | `argus-sandbox-worker` | — | Playwright sandbox analysis |
| `argus-threat-worker` | `argus-threat-worker` | — | CT log, NRD, threat feed ingest |
| `argus-security-worker` | `argus-security-worker` | — | Dynamic website security scans |
| `postgres` | `postgres:15` | 5432 | Relational database |
| `redis` | `redis:7` | 6379 | Job queues and caching |
| `prometheus` | `prom/prometheus` | 9090 | Metrics collection |
| `grafana` | `grafana/grafana` | 3000 | Dashboards |

---

## Prerequisites

### Local Development

- [Docker Desktop](https://docs.docker.com/get-docker/) ≥ 24.x  
- [Docker Compose](https://docs.docker.com/compose/) v2 (bundled with Docker Desktop)

### Kubernetes

- A running Kubernetes cluster (local: [minikube](https://minikube.sigs.k8s.io/), [kind](https://kind.sigs.k8s.io/), [k3s](https://k3s.io/); cloud: EKS, GKE, AKS)  
- [`kubectl`](https://kubernetes.io/docs/tasks/tools/) configured and pointing at the target cluster  
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server) installed (required for HPA)  
- Container images accessible from the cluster (build and push to a registry first)

---

## Local Development with Docker Compose

### Quick Start

```bash
# From the project root:
./scripts/dev_up.sh
```

This script will:

1. Create the `sandbox_artifacts/` host directory (bind-mounted into containers)
2. Pull latest infrastructure images
3. Build all four application images in parallel
4. Start the entire stack

### Service URLs

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |
| Health endpoint | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin) |
| PostgreSQL | `localhost:5432` — db: `argus`, user: `argus`, pass: `argus_dev_pass` |
| Redis | `localhost:6379` |

### Useful Commands

```bash
# View logs from a specific service
docker compose logs -f argus-api
docker compose logs -f argus-sandbox-worker

# Restart a single service
docker compose restart argus-api

# Scale a worker locally (for testing)
docker compose up -d --scale argus-sandbox-worker=3

# Stop all services (keeps volumes)
docker compose down

# Full reset (destroys all data volumes)
docker compose down -v
```

### Local Environment Overrides

Copy the example file and customize:

```bash
cp backend/.env.example .env.local
```

Then pass it to Compose:

```bash
docker compose --env-file .env.local up -d
```

### Sandbox Artifacts

Sandbox screenshots and DOM snapshots are written to `./sandbox_artifacts/` on the host (bind-mounted to `/data/sandbox` inside containers). This directory persists between restarts.

---

## Kubernetes Deployment

### Building & Pushing Images

Before deploying to Kubernetes, build and push images to a registry:

```bash
# Example using Docker Hub (replace 'yourorg' accordingly)
docker build -t yourorg/argus-api:latest ./backend
docker build -t yourorg/argus-sandbox-worker:latest -f ./backend/Dockerfile.sandbox ./backend
docker build -t yourorg/argus-threat-worker:latest   -f ./backend/Dockerfile.threat   ./backend
docker build -t yourorg/argus-security-worker:latest -f ./backend/Dockerfile.security ./backend

docker push yourorg/argus-api:latest
docker push yourorg/argus-sandbox-worker:latest
docker push yourorg/argus-threat-worker:latest
docker push yourorg/argus-security-worker:latest
```

> Update the `image:` fields in `deploy/k8s/deployments.yaml` and `deploy/k8s/infrastructure.yaml` to match your registry paths.

### Updating Secrets

> ⚠️ **Do not commit real secrets to Git.** Edit `deploy/k8s/secrets.yaml` locally or use an External Secrets Operator.

```bash
# Encode values manually
echo -n 'your-jwt-secret' | base64

# Or apply secrets from a .env file (not committed)
kubectl create secret generic argus-secrets \
  --from-literal=JWT_SECRET='...' \
  --from-literal=API_KEY_HASH_SECRET='...' \
  --from-literal=POSTGRES_PASSWORD='...' \
  --from-literal=POSTGRES_USER='argus' \
  --from-literal=POSTGRES_DB='argus' \
  -n argus --dry-run=client -o yaml | kubectl apply -f -
```

### Deploy

```bash
./scripts/k8s_deploy.sh
```

Manifests are applied in dependency order:

```
namespace → secrets → configmap → PVs → infrastructure → deployments → services → HPA
```

### Verify Deployment

```bash
# Watch pods come up
kubectl get pods -n argus -w

# Check rollout status
kubectl rollout status deployment/argus-api -n argus

# Check HPA
kubectl get hpa -n argus

# View API logs
kubectl logs -f deploy/argus-api -n argus

# Port-forward API locally
kubectl port-forward svc/argus-api-service 8000:80 -n argus
```

### Teardown

```bash
./scripts/k8s_delete.sh
```

> PersistentVolumes with `Retain` reclaim policy are **not** deleted automatically. Delete them manually if needed:
>
> ```bash
> kubectl delete pv sandbox-artifacts-pv
> ```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `REDIS_URL` | ✅ | — | Redis connection string |
| `JWT_SECRET` | ✅ | — | Secret for signing JWT tokens |
| `API_KEY_HASH_SECRET` | ✅ | — | Secret for hashing API keys |
| `OTLP_ENDPOINT` | ❌ | — | OpenTelemetry collector gRPC endpoint |
| `SANDBOX_STORAGE_ROOT` | ❌ | `/data/sandbox` | Directory for sandbox artifacts |
| `MODEL_PATH` | ❌ | `/app/models/model.joblib` | Path to the ensemble model file |
| `SAMPLE_PATH` | ❌ | `/app/sample_data/sample.csv` | Path to fallback sample data |
| `API_PORT` | ❌ | `8000` | Uvicorn listen port |

---

## Scaling Workers

### Docker Compose (local)

```bash
# Scale sandbox workers to 5
docker compose up -d --scale argus-sandbox-worker=5

# Scale security scanner workers
docker compose up -d --scale argus-security-worker=4
```

### Kubernetes (manual)

```bash
# Scale sandbox worker to 8 replicas
kubectl scale deployment argus-sandbox-worker --replicas=8 -n argus

# Scale security worker
kubectl scale deployment argus-security-worker --replicas=4 -n argus
```

### Kubernetes (automatic via HPA)

HPA is already configured for `argus-api` and `argus-sandbox-worker`:

| Deployment | Min | Max | CPU Trigger |
|---|---|---|---|
| `argus-api` | 2 | 10 | 70% |
| `argus-sandbox-worker` | 3 | 15 | 70% |

Check HPA status:

```bash
kubectl get hpa -n argus
kubectl describe hpa argus-api-hpa -n argus
```

> HPA requires [Metrics Server](https://github.com/kubernetes-sigs/metrics-server) to be installed in the cluster.

### Worker Tuning Tips

- **Sandbox worker** is the most resource-intensive (Chromium). Increase CPU/memory limits in `deployments.yaml` before scaling above 10 replicas.
- **Threat worker** should remain at `replicas: 1` to avoid duplicate CT log / NRD processing unless you implement distribution/deduplication logic.
- **Security worker** can scale freely; jobs are dequeued atomically from Redis.

---

## Monitoring & Metrics

### Prometheus

Prometheus scrapes the `/metrics` endpoint on `argus-api:8000` using:

- **Docker Compose:** DNS service discovery (`argus-api` hostname)
- **Kubernetes:** Pod annotation-based discovery (`prometheus.io/scrape: "true"`)

Available metrics include:

- `http_requests_total` — HTTP request count by method, status, path
- `http_request_duration_seconds` — request latency histogram
- `argus_scan_request_total` — phishing scan requests
- `argus_phishing_detections_total` — confirmed phishing detections
- `argus_queue_depth` — Redis job queue depth by worker type

### Grafana

Open http://localhost:3000 (local) or forward the `grafana-service` port (k8s).  
Credentials: `admin` / `admin` (change in production via `GF_SECURITY_ADMIN_PASSWORD`).

The `argus_dashboard.json` is provisioned automatically on startup.

### Health Endpoint

```
GET /health
```

Returns `200 OK` when healthy:

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok"
  },
  "timestamp": 1710000000.0
}
```

Returns `503 Service Unavailable` when degraded.

---

## Troubleshooting

### Docker Compose Issues

#### Containers exit immediately

```bash
docker compose logs argus-api
```

Common causes:
- Missing model file at `MODEL_PATH` — the API will auto-generate a dummy model if not found
- Database migration not run yet — the app calls `init_db()` on startup

#### Port already in use

```bash
# Find the conflicting process
lsof -i :8000
lsof -i :5432
```

Change host port mappings in `docker-compose.yml` if needed (e.g., `"8001:8000"`).

#### Sandbox worker fails to launch Chromium

The sandbox worker needs `SYS_ADMIN` capability and `shm_size: 1gb`. Verify these fields in `docker-compose.yml`. On Apple Silicon (M1/M2), use:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose build argus-sandbox-worker
```

### Kubernetes Issues

#### Pods stuck in `Pending`

```bash
kubectl describe pod <pod-name> -n argus
```

- **Insufficient resources:** increase node size or reduce resource `requests`
- **PVC not bound:** check PV/PVC status — `kubectl get pv,pvc -n argus`

#### HPA not scaling

```bash
kubectl describe hpa argus-api-hpa -n argus
```

- Ensure Metrics Server is installed: `kubectl top pods -n argus`
- Check that `resources.requests.cpu` is set on containers (required for HPA)

#### Pods in `CrashLoopBackOff`

```bash
kubectl logs <pod-name> -n argus --previous
```

Check for:
1. Missing `JWT_SECRET` or `API_KEY_HASH_SECRET` in secrets
2. Database unreachable — confirm `postgres-service` resolves correctly
3. Wrong `DATABASE_URL` format

#### Secrets not loading

```bash
kubectl get secret argus-secrets -n argus -o jsonpath='{.data}' | python3 -m json.tool
```

Verify that all expected keys (`JWT_SECRET`, `API_KEY_HASH_SECRET`, `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB`) are present.

#### Prometheus not scraping pods

```bash
kubectl get pods -n argus -o jsonpath='{.items[*].metadata.annotations}' | python3 -m json.tool
```

Ensure pods have the annotations:
```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

And that the `prometheus-sa` ServiceAccount has the ClusterRoleBinding applied.

---

## File Structure

```
deploy/
└── k8s/
    ├── namespace.yaml           # argus namespace
    ├── secrets.yaml             # JWT, API keys, DB password
    ├── configmap.yaml           # non-sensitive env config
    ├── persistent-volumes.yaml  # PV + PVC for sandbox artifacts
    ├── deployments.yaml         # all 4 application deployments
    ├── services.yaml            # ClusterIP / LoadBalancer services
    ├── infrastructure.yaml      # postgres, redis, prometheus, grafana
    └── hpa.yaml                 # horizontal pod autoscalers

backend/
├── Dockerfile                   # argus-api (multi-stage)
├── Dockerfile.sandbox           # argus-sandbox-worker (Playwright)
├── Dockerfile.threat            # argus-threat-worker
└── Dockerfile.security          # argus-security-worker

docker-compose.yml               # full local dev stack
scripts/
├── dev_up.sh                    # start local dev stack
├── k8s_deploy.sh                # deploy to k8s
└── k8s_delete.sh                # tear down from k8s

monitoring/
├── prometheus.yml               # compose Prometheus config
├── alert_rules.yml              # alerting rules
├── grafana_dashboard.json       # dashboard definition
└── grafana/
    └── provisioning/
        ├── datasources/prometheus.yml
        └── dashboards/argus.yml
```
