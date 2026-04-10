FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/fabell4/Hermes-dev"

WORKDIR /app

# Install dependencies first (cached layer unless requirements.txt changes)
# Create persistent directories in the same layer to avoid a separate RUN step
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/logs /app/data

# Copy source
COPY src/ ./src/

# Run as non-root user for security
RUN useradd --no-create-home --shell /bin/false hermes \
    && chown -R hermes:hermes /app
USER hermes

# Streamlit UI port + Prometheus /metrics port
EXPOSE 8501
EXPOSE 8000

# Run the Streamlit UI
# --server.headless=true suppresses browser-open attempts inside the container
CMD ["python", "-m", "streamlit", "run", "src/streamlit_app.py", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
