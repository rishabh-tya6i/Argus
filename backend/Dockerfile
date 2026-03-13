# ============================================================
# Stage 1 – dependency builder (cache-friendly)
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2 – runtime image
# ============================================================
FROM python:3.11-slim AS runtime

LABEL maintainer="Argus Team" \
      org.opencontainers.image.title="argus-api" \
      org.opencontainers.image.description="Argus Phishing Detection API"

WORKDIR /app

# Install runtime OS deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . /app

# Create non-root user for security
RUN addgroup --system argus && adduser --system --ingroup argus argus \
    && mkdir -p /data/sandbox /app/models \
    && chown -R argus:argus /app /data

USER argus

# Environment defaults (overridden at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_PORT=8000 \
    MODEL_PATH=/app/models/model.joblib \
    SAMPLE_PATH=/app/sample_data/sample.csv \
    SANDBOX_STORAGE_ROOT=/data/sandbox

EXPOSE 8000

# Health check for Docker / Compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]