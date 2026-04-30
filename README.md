# Hermes

**Hermes** is a self-hosted internet speed test monitoring solution that periodically tests your connection and exports results to multiple destinations. It features a modern React frontend, comprehensive REST API, and integrates seamlessly with your observability stack.

---

## ✨ Features

- **Automated Speed Testing** — Scheduled tests at configurable intervals with manual triggers
- **Multi-Destination Export** — CSV, SQLite, Prometheus, Loki
- **Modern Web UI** — React + Vite frontend with real-time charts and statistics
- **REST API** — Full-featured FastAPI backend for automation and integration
- **Alert Notifications** — Webhook, Gotify, ntfy, Apprise (100+ services)
- **Production-Ready** — Docker deployment, health checks, data retention policies
- **Security-First** — API key auth, rate limiting, SSRF protection, security headers

---

## 🚀 Quick Start

```bash
# Download docker-compose.yml and .env
curl -o docker-compose.yml https://raw.githubusercontent.com/fabell4/hermes/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/fabell4/hermes/main/.env.example

# Start containers
docker compose up -d

# Access the UI
open http://localhost:8080
```

The React UI will be available at `http://localhost:8080`.

---

## 📚 Documentation

**[View Full Documentation →](https://fabell4.github.io/hermes)**

- **[Getting Started](https://fabell4.github.io/hermes/getting-started)** — Deployment, configuration, and first steps
- **[Architecture](https://fabell4.github.io/hermes/architecture)** — System design, data flow, deployment topology
- **[API Reference](https://fabell4.github.io/hermes/api-reference)** — REST endpoints, authentication, examples
- **[Security](https://fabell4.github.io/hermes/security)** — Features, best practices, audit reports
- **[Alerts](https://fabell4.github.io/hermes/alerts)** — Setup guides for webhook, Gotify, ntfy, Apprise

---

## 🏗️ Architecture

Hermes runs as two Docker containers:

- **hermes-scheduler** — Background worker running speed tests on schedule, exposing Prometheus metrics, and pushing to Loki
- **hermes-api** — FastAPI REST API serving the React frontend and providing programmatic access

Both containers share volumes for `runtime_config.json`, `results.csv`, and `hermes.db`.

**Observability Integration:**
- **Prometheus** scrapes `:8000/metrics` every 15 seconds
- **Loki** receives push events on each test completion
- **Grafana** visualizes data from both sources with pre-built dashboard

See [Architecture Documentation](https://fabell4.github.io/hermes/architecture) for detailed diagrams.

---

## 🔒 Security

Hermes implements multiple layers of security:

- **API Key Authentication** — 32-character minimum enforced at startup
- **Rate Limiting** — Per-API-key sliding window (60 req/60s default) with Retry-After headers
- **SSRF Protection** — Alert URLs validated to block internal network access
- **Request Size Limits** — 1 MB default to prevent DoS attacks
- **Security Headers** — X-Frame-Options, X-Content-Type-Options, CORP, Referrer-Policy
- **Configurable CORS** — Restrict frontend origins via environment variable
- **130+ Security Tests** — Comprehensive test coverage for all security features

**Security Audit:** [APPROVED FOR v1.0 RELEASE](https://fabell4.github.io/hermes/SECURITY-AUDIT) after implementing all critical fixes.

See [Security Documentation](https://fabell4.github.io/hermes/security) for best practices and audit reports.

---

## 🛠️ Development Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install

# Run backend
python -m src.main  # Scheduler
uvicorn src.api.main:app --port 8080 --reload  # API

# Run frontend (separate terminal)
cd frontend && npm run dev

# Run tests
pytest
cd frontend && npm run type-check && npm run lint
```

---

## 📊 Data Collection

Each speed test captures:
- Download speed (Mbps)
- Upload speed (Mbps)
- Ping latency (ms)
- Jitter (ms)
- ISP name
- Timestamp (ISO 8601)

Results are exported to your choice of:
- **CSV** — Simple log file for manual inspection
- **SQLite** — Fast queries for UI and API (recommended)
- **Prometheus** — Time-series metrics for Grafana
- **Loki** — Structured logs for LogQL queries

---

## 🔔 Alert Notifications

Send notifications when consecutive test failures occur:

- **Configurable Threshold** — Alert after N consecutive failures
- **Cooldown Periods** — Prevent notification spam
- **Multiple Providers** — Webhook, Gotify, ntfy, Apprise (100+ services)
- **Test Notifications** — Verify configuration before deploying
- **UI or Environment Variables** — Configure via web UI or .env file

See [Alert Configuration Guide](https://fabell4.github.io/hermes/alerts) for setup instructions.

---

## 📈 Grafana Integration

Hermes includes a pre-built Grafana dashboard (`docs/grafana-dashboard.json`):

1. **Import Dashboard** via Grafana UI (+ → Import)
2. **Select Datasources** for Prometheus (metrics) and Loki (logs)
3. **View Insights:**
   - Download/upload trend charts
   - Ping/jitter statistics
   - Test failure annotations
   - ISP tracking

---

## 🐳 Docker Image

```bash
# Pull latest image
docker pull ghcr.io/fabell4/hermes:latest

# Run scheduler
docker run -d \
  --name hermes-scheduler \
  -p 8000:8000 \
  -v hermes-data:/app/data \
  ghcr.io/fabell4/hermes:latest \
  python -m src.main

# Run API
docker run -d \
  --name hermes-api \
  -p 8080:8080 \
  -v hermes-data:/app/data \
  ghcr.io/fabell4/hermes:latest
```

See [Getting Started Guide](https://fabell4.github.io/hermes/getting-started) for complete docker-compose setup.

---

## 📦 Environment Variables

Key configuration options (see [Getting Started](https://fabell4.github.io/hermes/getting-started) for complete list):

| Variable | Default | Description |
|---|---|---|
| `SPEEDTEST_INTERVAL_MINUTES` | `60` | How often to run speed tests |
| `ENABLED_EXPORTERS` | `csv` | Comma-separated: `csv`, `sqlite`, `prometheus`, `loki` |
| `API_KEY` | *(unset)* | API key for authentication (32+ chars, disables auth if empty) |
| `ALERT_FAILURE_THRESHOLD` | `0` | Consecutive failures before alerting (0 = disabled) |
| `PROMETHEUS_PORT` | `8000` | Port for /metrics scrape endpoint |
| `LOKI_URL` | *(unset)* | Loki push URL, e.g., `http://loki:3100` |

---

## 🧪 Test Coverage

- **344 tests passing** including 130+ API security tests
- **92% code coverage** (1,395 statements, 114 missed)
- **All ruff checks passing** (format + lint)
- **Comprehensive security validation:**
  - 15 SSRF protection tests
  - 6 request size limit tests
  - 7 test alert rate limiting tests
  - 25+ authentication tests
  - 18+ rate limiting tests
  - 30+ input validation tests

---

## 📄 License

Licensed under MIT. See [LICENSE](LICENSE) for details.

---

## 🤝 Support & Contributing

- **Documentation:** [https://fabell4.github.io/hermes](https://fabell4.github.io/hermes)
- **Issues:** [GitHub Issues](https://github.com/fabell4/hermes/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fabell4/hermes/discussions)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

## ⭐ Project Status

**Hermes v1.0 is in beta.** All four exporters (CSV, SQLite, Prometheus, Loki) are fully operational. Security audit complete and approved for release.

**Coming in v2.0:**
- Multi-user support with role-based access control
- API key rotation with zero-downtime
- Distributed rate limiting (Redis-backed)
- Secrets vault integration (HashiCorp Vault, AWS Secrets Manager)
- HSTS header support

See [TODO.md](TODO.md) for complete roadmap.
