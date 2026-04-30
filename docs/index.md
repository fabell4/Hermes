# Hermes Documentation

**Hermes** is a self-hosted internet speed test monitoring solution that periodically tests your connection and exports results to multiple destinations. It features a modern React frontend, comprehensive API, and integrates seamlessly with your observability stack.

---

## Features

### 🚀 Core Capabilities

- **Automated Speed Testing** — Scheduled tests at configurable intervals with manual triggers
- **Multi-Destination Export** — CSV, SQLite, Prometheus, Loki
- **Modern Web UI** — React + Vite frontend with real-time charts and statistics
- **REST API** — Full-featured FastAPI backend for automation and integration
- **Alert Notifications** — Webhook, Gotify, ntfy, Apprise (100+ services)
- **Production-Ready** — Docker deployment, health checks, data retention policies

### 📊 Data Collection

Each speed test captures:
- Download speed (Mbps)
- Upload speed (Mbps)
- Ping latency (ms)
- Jitter (ms)
- ISP name
- Timestamp

### 🔔 Alert System

Send notifications when consecutive test failures occur:
- Configurable failure threshold
- Cooldown periods to prevent spam
- Multiple provider support (webhook, Gotify, ntfy, Apprise)
- Test notifications before deploying
- UI or environment variable configuration

### 🔒 Security

- API key authentication with timing-attack prevention
- Per-key rate limiting with sliding windows
- SSRF protection on alert URLs
- Request size limits
- Security headers (X-Frame-Options, CSP, etc.)
- Input validation on all endpoints
- 130+ security-focused tests

---

## Quick Start

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

## Documentation

### 📘 Getting Started
**[Getting Started Guide](getting-started)** — Deployment, configuration, and first steps

### 🏗️ Architecture
**[Architecture Overview](architecture)** — System design, data flow, deployment topology

### 🔌 API Reference
**[API Documentation](api-reference)** — REST endpoints, authentication, examples

### 🔐 Security
**[Security Guide](security)** — Features, best practices, audit reports

### 🔔 Alerts
**[Alert Configuration](alerts)** — Setup guides for webhook, Gotify, ntfy, Apprise

### 📦 Release Process
**[Release Process](RELEASE-PROCESS)** — Checklist and workflow for releases

### 🛡️ Security Audit
**[Security Audit Report](SECURITY-AUDIT)** — Comprehensive security analysis (v1.0)

### ✨ Security Enhancements
**[Security Enhancements](SECURITY-ENHANCEMENTS)** — Implementation details of v1.0 security fixes

---

## Quick Links

- **[GitHub Repository](https://github.com/fabell4/hermes)** — Source code and issues
- **[Docker Image](https://github.com/fabell4/hermes/pkgs/container/hermes)** — ghcr.io/fabell4/hermes
- **[Grafana Dashboard](grafana-dashboard.json)** — Pre-built dashboard for import

---

## Environment Variables Reference

Key configuration options (see [Getting Started](getting-started) for complete list):

| Variable | Default | Description |
|---|---|---|
| `SPEEDTEST_INTERVAL_MINUTES` | `60` | How often to run speed tests |
| `ENABLED_EXPORTERS` | `csv` | Comma-separated: `csv`, `sqlite`, `prometheus`, `loki` |
| `API_KEY` | *(unset)* | API key for authentication (disables auth if empty) |
| `ALERT_FAILURE_THRESHOLD` | `0` | Consecutive failures before alerting (0 = disabled) |
| `PROMETHEUS_PORT` | `8000` | Port for /metrics scrape endpoint |
| `LOKI_URL` | *(unset)* | Loki push URL, e.g., `http://loki:3100` |

See [Getting Started](getting-started) for the full variable list with descriptions.

---

## Architecture at a Glance

Hermes runs as two containers:

- **hermes-scheduler** — Background worker running speed tests on schedule, exposing Prometheus metrics, and pushing to Loki
- **hermes-api** — FastAPI REST API serving the React frontend and providing programmatic access

Both containers share volumes for `runtime_config.json`, `results.csv`, and `hermes.db`.

**Observability Integration:**
- **Prometheus** scrapes `:8000/metrics` every 15 seconds
- **Loki** receives push events on each test completion
- **Grafana** visualizes data from both sources

See [Architecture](architecture) for detailed diagrams.

---

## Support & Contributing

- **Issues:** [GitHub Issues](https://github.com/fabell4/hermes/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fabell4/hermes/discussions)
- **Contributing:** See [README](https://github.com/fabell4/hermes#readme) for development setup

---

## License

Licensed under MIT. See [LICENSE](https://github.com/fabell4/hermes/blob/main/LICENSE) for details.
