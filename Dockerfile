FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/fabell4/hermes"

WORKDIR /app

# Install sqlite3 CLI + dependencies; create persistent dirs in same layer
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/logs /app/data

# Copy source
COPY src/ ./src/

# Run as non-root user for security
RUN useradd --create-home --shell /bin/false hermes \
    && chown -R hermes:hermes /app
USER hermes

# Streamlit UI port + Prometheus /metrics port + Health endpoint
EXPOSE 8501
EXPOSE 8000
EXPOSE 8080

# Health check — polls /health every 30s; 3 failures = unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8080/health', timeout=4); sys.exit(0)" || exit 1

# Run the Streamlit UI
# --server.headless=true suppresses browser-open attempts inside the container
CMD ["python", "-m", "streamlit", "run", "src/streamlit_app.py", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
