#!/usr/bin/env bash
# ===========================================================
# scripts/k8s_delete.sh – Tear down Argus from Kubernetes
# ===========================================================
set -euo pipefail

NAMESPACE="argus"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy/k8s"

echo "╔══════════════════════════════════════════════╗"
echo "║       Argus – Kubernetes Teardown            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "⚠  This will delete ALL Argus resources in namespace: $NAMESPACE"
echo "   PersistentVolumes with 'Retain' policy will NOT be automatically deleted."
echo ""
read -rp "   Are you sure? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "   Aborted."
  exit 0
fi

echo ""
echo "⟳  Deleting HPAs..."
kubectl delete -f "$MANIFEST_DIR/hpa.yaml" --ignore-not-found

echo "⟳  Deleting application deployments..."
kubectl delete -f "$MANIFEST_DIR/deployments.yaml" --ignore-not-found

echo "⟳  Deleting services..."
kubectl delete -f "$MANIFEST_DIR/services.yaml" --ignore-not-found

echo "⟳  Deleting infrastructure..."
kubectl delete -f "$MANIFEST_DIR/infrastructure.yaml" --ignore-not-found

echo "⟳  Deleting persistent volume claims..."
kubectl delete -f "$MANIFEST_DIR/persistent-volumes.yaml" --ignore-not-found

echo "⟳  Deleting configmap and secrets..."
kubectl delete -f "$MANIFEST_DIR/configmap.yaml" --ignore-not-found
kubectl delete -f "$MANIFEST_DIR/secrets.yaml" --ignore-not-found

echo "⟳  Deleting namespace (this may take a moment)..."
kubectl delete -f "$MANIFEST_DIR/namespace.yaml" --ignore-not-found

echo ""
echo "✔  Argus resources deleted."
echo "   PVs (sandbox-artifacts-pv) with Retain policy still exist."
echo "   To manually delete: kubectl delete pv sandbox-artifacts-pv"
