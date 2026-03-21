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

WORKDIR /src

# Install runtime OS deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source to /src/backend so 'import backend.app' works
COPY . /src/backend

# Create non-root user and ensure they have a home directory
RUN addgroup --system argus && adduser --system --ingroup argus --home /home/argus argus \
    && mkdir -p /data/sandbox /src/backend/models /home/argus/.cache \
    && chown -R argus:argus /src /data /home/argus

USER argus

WORKDIR /src/backend

# Environment defaults (overridden at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/src \
    HOME=/home/argus \
    HF_HOME=/home/argus/.cache/huggingface \
    API_PORT=8000 \
    MODEL_PATH=/src/backend/models/model.joblib \
    SAMPLE_PATH=/src/backend/sample_data/sample.csv \
    SANDBOX_STORAGE_ROOT=/data/sandbox

EXPOSE 8000

# Health check for Docker / Compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]