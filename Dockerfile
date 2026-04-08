# Stage 1: Builder - install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies needed for building packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Filter out Windows-only packages before installing
RUN grep -v -i "pywin32" requirements.txt > requirements-docker.txt && \
    pip install --no-cache-dir -r requirements-docker.txt


# Stage 2: Production image
FROM python:3.12-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash appuser

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

# Ensure src/ is on the Python path so internal imports (api.*, agent.*, etc.) resolve
ENV PYTHONPATH="/app/src:${PYTHONPATH}"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
