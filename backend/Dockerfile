# Multi-stage Dockerfile for QueryboxCore Backend
# Step 12.2: Deployment Infrastructure
# Target size: ~400-500MB (optimized for production)

# ============================================================================
# STAGE 1: Builder - Install dependencies and download models
# ============================================================================
FROM python:3.11-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
# Use production requirements (excludes dev dependencies)
COPY requirements-prod.txt requirements.txt

# Install Python packages to /install directory
RUN pip install --no-cache-dir --prefix=/install \
    --no-warn-script-location \
    -r requirements.txt

# NOTE: BGE-M3 model (~2GB) is downloaded on first container startup
# to keep the image size small (~400-500MB target).
# The model is cached in SENTENCE_TRANSFORMERS_HOME directory

# ============================================================================
# STAGE 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (app:app, UID 1000)
RUN groupadd -g 1000 app && \
    useradd -r -u 1000 -g app -s /bin/bash -m app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=app:app ./app ./app
COPY --chown=app:app ./alembic ./alembic
COPY --chown=app:app ./alembic.ini ./alembic.ini
COPY --chown=app:app ./scripts ./scripts

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH" \
    TRANSFORMERS_CACHE=/home/app/.cache/torch/sentence_transformers \
    SENTENCE_TRANSFORMERS_HOME=/home/app/.cache/torch/sentence_transformers

# Switch to non-root user
USER app

# Expose FastAPI port
EXPOSE 8000

# Health check endpoint
# Checks every 30s, timeout after 10s, start checking after 30s, retry 3 times
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
