---
layout: default
title: "Getting Started"
---

# Getting Started

This guide covers deployment, configuration, and first steps with Hermes.

---

## Quick Start with Docker Compose

The fastest way to get Hermes running:

```bash
# Create docker-compose.yml
curl -o docker-compose.yml https://raw.githubusercontent.com/fabell4/hermes/main/docker-compose.yml

# Create .env file
curl -o .env https://raw.githubusercontent.com/fabell4/hermes/main/.env.example

# Start containers
docker compose up -d

# Access the UI
open http://localhost:8080
```

The React UI will be available at `http://localhost:8080`.

---

## Self-Hosting Guide

Hermes runs as two containers from the same Docker image:

- **hermes-scheduler** — Background worker running speed tests on schedule
- **hermes-api** — FastAPI REST API serving the React frontend

### Minimal docker-compose.yml

Create a `docker-compose.yml` on your server:

```yaml
services:
  hermes-scheduler:
    image: ghcr.io/fabell4/hermes:latest
    container_name: hermes-scheduler
    restart: always
    command: ["python", "-m", "src.main"]
    ports:
      - "${PROMETHEUS_PORT:-8000}:8000" # Prometheus /metrics endpoint
    volumes:
      - hermes-logs:/app/logs           # CSV result history + hermes.log
      - hermes-data:/app/data           # runtime_config.json, .run_trigger, hermes.db
    environment:
      APP_ENV: "${APP_ENV:-production}"
      LOG_LEVEL: "${LOG_LEVEL:-INFO}"
      TZ: "${TZ:-UTC}"
      SPEEDTEST_INTERVAL_MINUTES: "${SPEEDTEST_INTERVAL_MINUTES:-60}"
      RUN_ON_STARTUP: "${RUN_ON_STARTUP:-true}"
      ENABLED_EXPORTERS: "${ENABLED_EXPORTERS:-csv}"
      CSV_LOG_PATH: "logs/results.csv"
      SQLITE_DB_PATH: "data/hermes.db"
      PROMETHEUS_PORT: "${PROMETHEUS_PORT:-8000}"
      LOKI_URL: "${LOKI_URL:-}"
      LOKI_JOB_LABEL: "${LOKI_JOB_LABEL:-hermes_speedtest}"
      # Alert configuration (optional) - see Alerts section
      ALERT_FAILURE_THRESHOLD: "${ALERT_FAILURE_THRESHOLD:-0}"
      ALERT_COOLDOWN_MINUTES: "${ALERT_COOLDOWN_MINUTES:-60}"
      ALERT_WEBHOOK_URL: "${ALERT_WEBHOOK_URL:-}"
      ALERT_GOTIFY_URL: "${ALERT_GOTIFY_URL:-}"
      ALERT_GOTIFY_TOKEN: "${ALERT_GOTIFY_TOKEN:-}"
      ALERT_GOTIFY_PRIORITY: "${ALERT_GOTIFY_PRIORITY:-5}"
      ALERT_NTFY_URL: "${ALERT_NTFY_URL:-https://ntfy.sh}"
      ALERT_NTFY_TOPIC: "${ALERT_NTFY_TOPIC:-}"
      ALERT_NTFY_TOKEN: "${ALERT_NTFY_TOKEN:-}"
      ALERT_NTFY_PRIORITY: "${ALERT_NTFY_PRIORITY:-3}"
      ALERT_NTFY_TAGS: "${ALERT_NTFY_TAGS:-warning,rotating_light}"
      ALERT_APPRISE_URL: "${ALERT_APPRISE_URL:-}"
    env_file:
      - path: .env
        required: false

  hermes-api:
    image: ghcr.io/fabell4/hermes:latest
    container_name: hermes-api
    restart: always
    ports:
      - "${API_PORT:-8080}:8080"        # FastAPI REST + React SPA
    volumes:
      - hermes-logs:/app/logs
      - hermes-data:/app/data
    environment:
      APP_ENV: "${APP_ENV:-production}"
      APP_VERSION: "${APP_VERSION:-dev}"
      LOG_LEVEL: "${LOG_LEVEL:-INFO}"
      TZ: "${TZ:-UTC}"
      SPEEDTEST_INTERVAL_MINUTES: "${SPEEDTEST_INTERVAL_MINUTES:-60}"
      ENABLED_EXPORTERS: "${ENABLED_EXPORTERS:-csv}"
      CSV_LOG_PATH: "logs/results.csv"
      SQLITE_DB_PATH: "data/hermes.db"
      API_KEY: "${API_KEY:-}"
      RATE_LIMIT_PER_MINUTE: "${RATE_LIMIT_PER_MINUTE:-60}"
    env_file:
      - path: .env
        required: false
    depends_on:
      - hermes-scheduler

volumes:
  hermes-logs:
    driver: local
  hermes-data:
    driver: local
```

### Configuration via .env

Create a `.env` file alongside `docker-compose.yml`. The `.env.example` in the repo lists every variable with comments:

```bash
curl -o .env https://raw.githubusercontent.com/fabell4/hermes/main/.env.example
```

**Key `.env` variables:**

| Variable | Default | Description |
| --- | --- | --- |
| `TZ` | `UTC` | IANA timezone name for log timestamps |
| `ENABLED_EXPORTERS` | `csv` | Comma-separated: `csv`, `sqlite`, `prometheus`, `loki` |
| `SPEEDTEST_INTERVAL_MINUTES` | `60` | How often to run speed tests |
| `RUN_ON_STARTUP` | `true` | Run a test immediately on container start |
| `CSV_LOG_PATH` | `logs/results.csv` | Path to CSV results file |
| `CSV_MAX_ROWS` | `0` (unlimited) | Maximum CSV rows to keep |
| `CSV_RETENTION_DAYS` | `0` (unlimited) | Delete CSV rows older than N days |
| `SQLITE_DB_PATH` | `data/hermes.db` | Path to SQLite database |
| `SQLITE_MAX_ROWS` | `0` (unlimited) | Maximum SQLite rows to keep |
| `SQLITE_RETENTION_DAYS` | `0` (unlimited) | Delete SQLite rows older than N days |
| `PROMETHEUS_PORT` | `8000` | Port for `/metrics` scrape endpoint |
| `LOKI_URL` | *(unset)* | Loki push URL, e.g., `http://loki:3100` |
| `LOKI_JOB_LABEL` | `hermes_speedtest` | Job label for Loki log entries |
| `API_PORT` | `8080` | Host port for FastAPI + React frontend |
| `API_KEY` | *(unset)* | API key for auth (disables auth if unset) |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max write requests per API key per 60s |
| `ALERT_FAILURE_THRESHOLD` | `0` (disabled) | Consecutive failures before alerting |
| `ALERT_COOLDOWN_MINUTES` | `60` | Minimum minutes between alerts |

See [Alert Configuration](alerts) for alert-related environment variables.

### Start the Containers

```bash
docker compose up -d
```

Check logs:

```bash
docker logs hermes-scheduler
docker logs hermes-api
```

### Enable SQLite for Best UI Experience

The React dashboard reads from `hermes.db` when available and falls back to `results.csv` otherwise. Add `sqlite` to `ENABLED_EXPORTERS`:

```bash
ENABLED_EXPORTERS=csv,sqlite
```

Then restart:

```bash
docker compose restart
```

---

## Building from Source

If you prefer to build the Docker image locally instead of using the pre-built image:

### Building Docker Image

```bash
# Clone the repository
git clone https://github.com/fabell4/hermes.git
cd hermes

# Build the image
docker build -t hermes:local .

# Use the local image in docker-compose
export HERMES_IMAGE=hermes:local
docker compose up -d
```

### Running Directly with Python (Without Docker)

For production deployment without Docker:

**Prerequisites:**

- Python 3.12+
- **Ookla speedtest CLI** — Download and install from <https://www.speedtest.net/apps/cli>
  - On Debian/Ubuntu: Follow the official installation script
  - On macOS: `brew install speedtest-cli` (official Ookla CLI)
  - On Windows: Download the installer from the official Ookla website
  - The `speedtest` binary must be available in your system PATH

```bash
# Install Python 3.12+
python --version  # Verify Python 3.12 or higher

# Verify Ookla CLI is installed
speedtest --version  # Should show "Speedtest by Ookla"

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the scheduler (background worker)
python -m src.main
```

In a separate terminal (or systemd service), run the API server:

```bash
# Activate virtual environment first
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8080
```

**Note:** For production deployments, consider using:

- **systemd** service units to manage both processes
- **Gunicorn** or **Hypercorn** for the FastAPI server
- **Process manager** like supervisord to ensure both services restart on failure

---

## Development Setup

For local development with hot reload:

### Prerequisites

- Python 3.12+
- Node.js 18+
- Virtual environment (venv)
- **Ookla speedtest CLI** — Install from <https://www.speedtest.net/apps/cli>

### Backend Setup

1. **Create and activate virtual environment:**

   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   ```bash
   copy .env.example .env
   ```

4. **Run scheduler:**

   ```bash
   python -m src.main
   ```

5. **Run API server (separate terminal):**

   ```bash
   uvicorn src.api.main:app --port 8080 --reload
   ```

### Frontend Setup

1. **Install frontend dependencies:**

   ```bash
   cd frontend
   npm install
   ```

2. **Start dev server:**

   ```bash
   npm run dev
   ```

   The dev server proxies API calls to `:8080` automatically.

### Running Tests

**Python tests with coverage:**

```bash
pytest
```

**Frontend type-check + lint:**

```bash
cd frontend
npm run type-check
npm run lint
```

### VS Code Tasks

Use pre-configured tasks (Terminal → Run Task):

- **Run Hermes** — Start Python scheduler
- **Run Hermes UI** — Start Streamlit UI (legacy)
- **Run Hermes API** — Start FastAPI server
- **Run Hermes Frontend (dev)** — Start React dev server

---

## First Steps

### 1. Access the Web UI

Navigate to `http://localhost:8080` (or your server IP).

### 2. View Dashboard

The **Dashboard** page shows:

- Latest speed test result
- Download/upload trend charts
- Ping/jitter statistics
- Historical data (if SQLite enabled)

### 3. Trigger Manual Test

Click **"Run Speed Test"** on the Dashboard to trigger an on-demand test.

### 4. Configure Settings

Navigate to **Settings** to adjust:

- **Test interval** — How often to run automatic tests
- **Enabled exporters** — Which destinations to write results to
- **Alert settings** — Configure failure notifications (see [Alerts](alerts))

Changes are saved to `data/runtime_config.json` and apply immediately (no restart required).

### 5. Integrate with Observability Stack

**Prometheus:**

- Add scrape job targeting `http://<hermes-host>:8000/metrics`
- Scrape interval: 15 seconds recommended

**Loki:**

- Set `LOKI_URL=http://loki:3100` in `.env`
- Hermes pushes on each test completion

**Grafana:**

- Import dashboard from `docs/grafana-dashboard.json`
- Configure Prometheus and Loki datasources
- View download/upload/ping trends with annotations

---

## Troubleshooting

### Container Won't Start

Check logs:

```bash
docker logs hermes-scheduler
docker logs hermes-api
```

Common issues:

- **Port already in use:** Change `API_PORT` or `PROMETHEUS_PORT` in `.env`
- **Missing .env file:** Ensure `.env` exists or remove `required: true` from `docker-compose.yml`
- **Invalid API_KEY length:** Must be 32+ characters if set

### No Results in UI

1. **Check scheduler logs:**

   ```bash
   docker logs hermes-scheduler
   ```

2. **Verify test interval:**

   ```bash
   curl http://localhost:8080/api/config
   ```

3. **Trigger manual test:**

   ```bash
   curl -X POST http://localhost:8080/api/trigger
   ```

4. **Check SQLite enabled:**

   ```bash
   ENABLED_EXPORTERS=csv,sqlite
   ```

### Prometheus Metrics Not Scraping

1. **Verify `/metrics` endpoint:**

   ```bash
   curl http://localhost:8000/metrics
   ```

2. **Check Prometheus scrape config:**

   ```yaml
   scrape_configs:
     - job_name: 'hermes'
       scrape_interval: 15s
       static_configs:
         - targets: ['hermes-scheduler:8000']
   ```

3. **Check port exposure in `docker-compose.yml`:**

   ```yaml
   ports:
     - "8000:8000"
   ```

### Loki Logs Not Appearing

1. **Verify `LOKI_URL` is set:**

   ```bash
   docker exec hermes-scheduler printenv LOKI_URL
   ```

2. **Check Loki is reachable:**

   ```bash
   docker exec hermes-scheduler curl $LOKI_URL/ready
   ```

3. **Enable loki exporter:**

   ```bash
   ENABLED_EXPORTERS=csv,sqlite,loki
   ```

### Authentication Errors

When `API_KEY` is set, protected endpoints require `X-Api-Key` header:

```bash
curl -X POST http://localhost:8080/api/trigger \
  -H "X-Api-Key: your-api-key-here"
```

**Generate secure key:**

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

### Rate Limit Exceeded

Response `429 Too Many Requests` means you've exceeded `RATE_LIMIT_PER_MINUTE` (default: 60 requests per 60 seconds).

Check `Retry-After` header for wait time:

```bash
curl -i http://localhost:8080/api/trigger -H "X-Api-Key: key"
```

Adjust rate limit in `.env`:

```bash
RATE_LIMIT_PER_MINUTE=120
```

---

## Next Steps

- **[Configure Alerts](alerts)** — Set up failure notifications
- **[Explore API](api-reference)** — Automate with REST endpoints
- **[Review Security](security)** — Production best practices
- **[View Architecture](architecture)** — Understand system design

---

## Support

- **Issues:** [GitHub Issues](https://github.com/fabell4/hermes/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fabell4/hermes/discussions)
- **Changelog:** [CHANGELOG.md](https://github.com/fabell4/hermes/blob/main/CHANGELOG.md)
