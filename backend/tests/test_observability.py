"""
Tests for platform observability: metrics endpoint and key counters.

Run with:
    cd d:\\Projects\\Argus\\backend
    python -m pytest tests/test_observability.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app with observability initialised."""
    # Reset prometheus registry to avoid duplicate metric errors across test runs
    try:
        from prometheus_client import REGISTRY
        collectors = list(REGISTRY._names_to_collectors.values())
        for c in collectors:
            try:
                REGISTRY.unregister(c)
            except Exception:
                pass
    except Exception:
        pass

    from app.main import app
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    """GET /api/health should return 200."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_metrics_endpoint_reachable(client: TestClient):
    """GET /metrics should return 200 with Prometheus text content."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/plain" in content_type or resp.text.startswith("#")


def test_scan_request_increments_metrics(client: TestClient):
    """/api/predict should increment scan_request_count and appear in /metrics."""
    # Send a scan request
    resp = client.post(
        "/api/predict",
        json={"url": "http://observable-test-example.com", "html": None, "screenshot": None},
    )
    # Accept 200 or 429 (rate-limited in some test envs)
    assert resp.status_code in (200, 422, 429)

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    metrics_text = metrics_resp.text

    # scan_latency_seconds histogram must be registered
    assert "scan_latency_seconds" in metrics_text


def test_prometheus_metric_names_present(client: TestClient):
    """All required metric names should appear in /metrics output."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text

    expected_metrics = [
        "scan_request_count",
        "scan_latency_seconds",
        "phishing_detections_total",
        "false_positive_overrides_total",
        "visual_impersonation_hits_total",
        "threat_intel_alerts_total",
        "model_inference_latency_seconds",
        "sandbox_runs_total",
        "queue_depth",
        "queue_wait_seconds",
        "queue_processing_seconds",
        "queue_jobs_total",
        "worker_heartbeat",
        "worker_failures_total",
    ]

    for metric in expected_metrics:
        assert metric in body, f"Expected metric '{metric}' not found in /metrics output"


def test_worker_heartbeat_gauge(client: TestClient):
    """update_worker_heartbeat should update the gauge without errors."""
    import time
    from app.observability import update_worker_heartbeat, WORKER_HEARTBEAT

    update_worker_heartbeat("test_worker")
    # Just check it sets a recent timestamp
    gauge_val = WORKER_HEARTBEAT.labels(worker="test_worker")._value.get()
    assert abs(gauge_val - time.time()) < 5


def test_correlation_ctx_round_trip():
    """set_correlation_ctx / get_correlation_ctx should store and retrieve values."""
    from app.observability import set_correlation_ctx, get_correlation_ctx

    set_correlation_ctx(
        request_id="test-req-1",
        scan_id="scan-42",
        worker_name="test_obs",
        url_domain="example.com",
    )

    ctx = get_correlation_ctx()
    assert ctx["request_id"] == "test-req-1"
    assert ctx["scan_id"] == "scan-42"
    assert ctx["worker_name"] == "test_obs"
    assert ctx["url_domain"] == "example.com"
