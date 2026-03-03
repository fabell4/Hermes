FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cached layer unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Streamlit default port
EXPOSE 8501

# Run the Streamlit UI
CMD ["python", "-m", "streamlit", "run", "src/streamlit_app.py", "--server.address=0.0.0.0"]
