#!/usr/bin/env bash
# ===========================================================
# scripts/k8s_deploy.sh – Deploy Argus to Kubernetes
# ===========================================================
set -euo pipefail

MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy/k8s"
NAMESPACE="argus"

echo "╔══════════════════════════════════════════════╗"
echo "║       Argus – Kubernetes Deploy              ║"
echo "╚══════════════════════════════════════════════╝"

# Verify kubectl is available
if ! command -v kubectl &>/dev/null; then
  echo "✗  kubectl not found. Install kubectl and configure your kubeconfig."
  exit 1
fi

echo "➤  Current context: $(kubectl config current-context)"
echo ""

# 1. Namespace first
echo "⟳  Applying namespace..."
kubectl apply -f "$MANIFEST_DIR/namespace.yaml"

# 2. Secrets (ensure fresh before config because deployments reference them)
echo "⟳  Applying secrets..."
kubectl apply -f "$MANIFEST_DIR/secrets.yaml"

# 3. ConfigMap
echo "⟳  Applying configmap..."
kubectl apply -f "$MANIFEST_DIR/configmap.yaml"

# 4. Persistent volumes
echo "⟳  Applying persistent volumes..."
kubectl apply -f "$MANIFEST_DIR/persistent-volumes.yaml"

# 5. Infrastructure (Postgres, Redis, Prometheus, Grafana)
echo "⟳  Applying infrastructure (postgres, redis, prometheus, grafana)..."
kubectl apply -f "$MANIFEST_DIR/infrastructure.yaml"

# 6. Application deployments
echo "⟳  Applying application deployments..."
kubectl apply -f "$MANIFEST_DIR/deployments.yaml"

# 7. Services
echo "⟳  Applying services..."
kubectl apply -f "$MANIFEST_DIR/services.yaml"

# 8. HPAs (requires metrics-server in cluster)
echo "⟳  Applying horizontal pod autoscalers..."
kubectl apply -f "$MANIFEST_DIR/hpa.yaml"

# 9. Wait for rollout
echo ""
echo "⟳  Waiting for rollouts to complete..."
kubectl rollout status deployment/argus-api -n "$NAMESPACE" --timeout=120s
kubectl rollout status deployment/argus-sandbox-worker -n "$NAMESPACE" --timeout=120s
kubectl rollout status deployment/argus-threat-worker -n "$NAMESPACE" --timeout=120s
kubectl rollout status deployment/argus-security-worker -n "$NAMESPACE" --timeout=120s

echo ""
echo "✔  All deployments are ready!"
echo ""
echo "   Pods:     kubectl get pods -n $NAMESPACE"
echo "   Services: kubectl get svc  -n $NAMESPACE"
echo "   HPA:      kubectl get hpa  -n $NAMESPACE"
echo "   Logs:     kubectl logs -f deploy/argus-api -n $NAMESPACE"
