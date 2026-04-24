# ---------------------------------------------------------------------------
# Stage 1 — Build the React/Vite frontend
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python application image
# ---------------------------------------------------------------------------
FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/fabell4/hermes"

# Injected by the CI build pipeline from the git tag (e.g. v0.3.0 → 0.3.0).
# Falls back to "dev" for local builds.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app

# Install sqlite3 CLI + dependencies; create persistent dirs in same layer
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/logs /app/data

# Copy source
COPY src/ ./src/

# Copy the pre-built React frontend (served by FastAPI at runtime)
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Run as non-root user for security
RUN useradd --create-home --shell /bin/false hermes \
    && chown -R hermes:hermes /app
USER hermes

# Prometheus /metrics port + Health/API endpoint
EXPOSE 8000
EXPOSE 8080

# Health check — polls /health every 30s; 3 failures = unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8080/api/health', timeout=4); sys.exit(0)" || exit 1

# Run the FastAPI server (serves the React SPA + REST API)
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
