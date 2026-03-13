#!/usr/bin/env bash
# ===========================================================
# scripts/dev_up.sh – Start Argus local development stack
# ===========================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════╗"
echo "║        Argus – Local Dev Stack               ║"
echo "╚══════════════════════════════════════════════╝"

# Create local bind-mount directory for sandbox artifacts
mkdir -p sandbox_artifacts
echo "✔  sandbox_artifacts/ directory ready"

# Pull latest images for infrastructure services
echo "⟳  Pulling base images..."
docker compose pull postgres redis prometheus grafana --quiet 2>/dev/null || true

# Build application images
echo "⟳  Building application images..."
docker compose build --parallel

# Start all services
echo "⟳  Starting services..."
docker compose up -d

echo ""
echo "✔  Stack is up! Services:"
echo ""
echo "   API        →  http://localhost:8000"
echo "   API Docs   →  http://localhost:8000/docs"
echo "   Metrics    →  http://localhost:8000/metrics"
echo "   Prometheus →  http://localhost:9090"
echo "   Grafana    →  http://localhost:3000  (admin / admin)"
echo "   PostgreSQL →  localhost:5432         (argus / argus_dev_pass)"
echo "   Redis      →  localhost:6379"
echo ""
echo "   Logs:  docker compose logs -f [service-name]"
echo "   Stop:  docker compose down"
echo "   Reset: docker compose down -v   (removes volumes)"
