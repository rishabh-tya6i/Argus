"""
Argus Observability Module
==========================

Single import point for all observability tooling:
  - OpenTelemetry tracing (OTLP gRPC exporter)
  - Structured JSON logging (python-json-logger) with contextvars correlation
  - Prometheus metrics (prometheus-client)

Usage in any module:
    from .observability import tracer, logger, metrics
    from .observability import SCAN_REQUEST_COUNT, SCAN_LATENCY, ...
    from .observability import set_correlation_ctx, get_correlation_ctx
"""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Optional, cast

_cv_request_id: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("request_id", default=None))
_cv_scan_id: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("scan_id", default=None))
_cv_sandbox_run_id: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("sandbox_run_id", default=None))
_cv_tenant_id: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("tenant_id", default=None))
_cv_worker_name: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("worker_name", default=None))
_cv_detection_type: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("detection_type", default=None))
_cv_url_domain: ContextVar[str | None] = cast(ContextVar[str | None], ContextVar("url_domain", default=None))




def set_correlation_ctx(
    *,
    request_id: Optional[str] = None,
    scan_id: Optional[str] = None,
    sandbox_run_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    worker_name: Optional[str] = None,
    detection_type: Optional[str] = None,
    url_domain: Optional[str] = None,
) -> None:
    """Set correlation context variables for the current async task / thread."""
    if request_id is not None:
        _cv_request_id.set(request_id)
    if scan_id is not None:
        _cv_scan_id.set(scan_id)
    if sandbox_run_id is not None:
        _cv_sandbox_run_id.set(sandbox_run_id)
    if tenant_id is not None:
        _cv_tenant_id.set(tenant_id)
    if worker_name is not None:
        _cv_worker_name.set(worker_name)
    if detection_type is not None:
        _cv_detection_type.set(detection_type)
    if url_domain is not None:
        _cv_url_domain.set(url_domain)


def get_correlation_ctx() -> dict:
    """Return all current correlation fields as a dict (None values omitted)."""
    ctx = {
        "request_id": _cv_request_id.get(),
        "scan_id": _cv_scan_id.get(),
        "sandbox_run_id": _cv_sandbox_run_id.get(),
        "tenant_id": _cv_tenant_id.get(),
        "worker_name": _cv_worker_name.get(),
        "detection_type": _cv_detection_type.get(),
        "url_domain": _cv_url_domain.get(),
    }
    return {k: v for k, v in ctx.items() if v is not None}


# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------

class _CorrelationFilter(logging.Filter):
    """Injects correlation context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_correlation_ctx()
        for key, value in ctx.items():
            setattr(record, key, value)
        # Ensure fields are always present (even as None) so formatters don't fail
        for field in ("request_id", "scan_id", "sandbox_run_id", "tenant_id",
                      "worker_name", "detection_type", "url_domain"):
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


def setup_logging() -> None:
    """Configure root logger to emit newline-delimited JSON suitable for Loki/Datadog/ELK."""
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore

        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            fmt=(
                "%(asctime)s %(name)s %(levelname)s %(message)s "
                "%(request_id)s %(scan_id)s %(sandbox_run_id)s "
                "%(tenant_id)s %(worker_name)s %(detection_type)s %(url_domain)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(_CorrelationFilter())

        root = logging.getLogger()
        # Remove any existing handlers to avoid duplicate output
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    except ImportError:
        # Fall back to standard logging if python-json-logger not installed
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )
        logging.getLogger(__name__).warning(
            "python-json-logger not installed; using plain text logging."
        )


# ---------------------------------------------------------------------------
# OpenTelemetry Tracing
# ---------------------------------------------------------------------------

def setup_tracing() -> None:
    """Initialise OpenTelemetry with an OTLP gRPC exporter.

    Reads OTLP_ENDPOINT from env (default: http://localhost:4317).
    If the OTLP exporter packages are not installed the function degrades
    gracefully to a no-op tracer so the rest of the code is unaffected.
    """
    endpoint = os.environ.get("OTLP_ENDPOINT", "http://localhost:4317")
    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore
        from opentelemetry.sdk.resources import Resource  # type: ignore

        resource = Resource.create({"service.name": "argus-phishguard"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logging.getLogger(__name__).info(
            "OpenTelemetry tracing initialised", extra={"otlp_endpoint": endpoint}
        )
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).warning(
            f"OpenTelemetry setup failed ({exc}); using no-op tracer."
        )


def get_tracer(name: str = "argus"):
    """Return an OpenTelemetry tracer (or no-op if OTel not installed)."""
    try:
        from opentelemetry import trace  # type: ignore
        return trace.get_tracer(name)
    except ImportError:
        return _NoopTracer()


class _NoopSpan:
    """Minimal no-op span context manager used when OTel is unavailable."""
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def set_attribute(self, *_): pass
    def record_exception(self, *_): pass
    def set_status(self, *_): pass


class _NoopTracer:
    def start_as_current_span(self, name: str, **_):
        return _NoopSpan()


# Module-level tracer — import this in other modules.
tracer = get_tracer("argus")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

try:
    from prometheus_client import (  # type: ignore
        Counter, Histogram, Gauge, REGISTRY,
    )

    # -- Scan metrics --
    SCAN_REQUEST_COUNT = Counter(
        "scan_request_count",
        "Total scan requests received",
        ["tenant_plan", "prediction"],
    )
    SCAN_LATENCY = Histogram(
        "scan_latency_seconds",
        "End-to-end scan latency in seconds",
        ["tenant_plan"],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
    )

    # -- Detection quality / business metrics --
    PHISHING_DETECTIONS_TOTAL = Counter(
        "phishing_detections_total",
        "Total phishing predictions made",
        ["detection_type", "tenant_plan"],
    )
    FALSE_POSITIVE_OVERRIDES_TOTAL = Counter(
        "false_positive_overrides_total",
        "User-reported false positives",
        ["tenant_plan"],
    )
    VISUAL_IMPERSONATION_HITS_TOTAL = Counter(
        "visual_impersonation_hits_total",
        "Visual brand impersonation hits detected",
    )
    THREAT_INTEL_ALERTS_TOTAL = Counter(
        "threat_intel_alerts_total",
        "Total threat intelligence alerts generated",
        ["detection_type"],
    )

    ALERTS_GENERATED_TOTAL = Counter(
        "alerts_generated_total",
        "Total security alerts generated",
        ["alert_type", "severity"],
    )
    ALERTS_SENT_TOTAL = Counter(
        "alerts_sent_total",
        "Total security alerts sent to notification channels",
        ["type"],
    )
    ALERTS_FAILED_TOTAL = Counter(
        "alerts_failed_total",
        "Total security alert notification failures",
        ["type"],
    )
    ALERTS_BY_SEVERITY = Gauge(
        "alerts_by_severity",
        "Current number of open alerts by severity level",
        ["severity"],
    )

    # -- Model inference --
    MODEL_INFERENCE_LATENCY = Histogram(
        "model_inference_latency_seconds",
        "Per-detector inference latency",
        ["detector"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
    )

    # -- Sandbox --
    SANDBOX_RUNS_TOTAL = Counter(
        "sandbox_runs_total",
        "Total sandbox runs by status",
        ["status"],
    )

    # -- Queue metrics --
    QUEUE_DEPTH = Gauge(
        "queue_depth",
        "Current number of jobs in the worker queue",
        ["worker"],
    )
    QUEUE_WAIT_SECONDS = Histogram(
        "queue_wait_seconds",
        "Time a job waits in the queue before processing",
        ["worker"],
        buckets=(0.5, 1, 5, 10, 30, 60, 120, 300),
    )
    QUEUE_PROCESSING_SECONDS = Histogram(
        "queue_processing_seconds",
        "Worker job execution time",
        ["worker"],
        buckets=(0.5, 1, 5, 10, 30, 60, 120, 300),
    )
    QUEUE_JOBS_TOTAL = Counter(
        "queue_jobs_total",
        "Total jobs processed by workers",
        ["worker", "status"],
    )

    # -- Worker health --
    WORKER_HEARTBEAT = Gauge(
        "worker_heartbeat",
        "Unix timestamp of the last worker heartbeat",
        ["worker"],
    )
    WORKER_FAILURES_TOTAL = Counter(
        "worker_failures_total",
        "Total unhandled worker failures",
        ["worker"],
    )

    _PROMETHEUS_AVAILABLE = True

except ImportError:  # pragma: no cover
    # Stubs so imports don't break when prometheus-client is not installed
    _PROMETHEUS_AVAILABLE = False

    class _Stub:
        def labels(self, **_): return self
        def inc(self, *_): pass
        def observe(self, *_): pass
        def set(self, *_): pass
        def time(self): return _StubCtx()

    class _StubCtx:
        def __enter__(self): return self
        def __exit__(self, *_): pass

    _stub = _Stub()
    SCAN_REQUEST_COUNT = _stub
    SCAN_LATENCY = _stub
    PHISHING_DETECTIONS_TOTAL = _stub
    FALSE_POSITIVE_OVERRIDES_TOTAL = _stub
    VISUAL_IMPERSONATION_HITS_TOTAL = _stub
    THREAT_INTEL_ALERTS_TOTAL = _stub
    MODEL_INFERENCE_LATENCY = _stub
    SANDBOX_RUNS_TOTAL = _stub
    QUEUE_DEPTH = _stub
    QUEUE_WAIT_SECONDS = _stub
    QUEUE_PROCESSING_SECONDS = _stub
    QUEUE_JOBS_TOTAL = _stub
    WORKER_HEARTBEAT = _stub
    WORKER_FAILURES_TOTAL = _stub
    ALERTS_GENERATED_TOTAL = _stub
    ALERTS_SENT_TOTAL = _stub
    ALERTS_FAILED_TOTAL = _stub
    ALERTS_BY_SEVERITY = _stub


def update_worker_heartbeat(worker: str) -> None:
    """Update the worker heartbeat gauge with the current Unix timestamp."""
    WORKER_HEARTBEAT.labels(worker=worker).set(time.time())


# ---------------------------------------------------------------------------
# Initialise everything when not running under pytest (workers / uvicorn)
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)
