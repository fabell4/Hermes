---
layout: home
title: "Hermes Documentation"
description: "Self-hosted internet speed test monitoring with modern observability stack integration"
show_header: false

hero_title: "Hermes Docs"
hero_subtitle: "Self-hosted internet speed test monitoring with automated scheduling, multi-destination export, and full observability stack integration."
hero_cta:
  - label: "Get Started"
    url: /getting-started
    primary: true
  - label: "View on GitHub"
    url: https://github.com/fabell4/hermes

quick_links:
  - title: "Getting Started"
    url: /getting-started
    icon: "🚀"
    description: "Deploy with Docker, configure exporters, and run your first speed test."
  - title: "Architecture"
    url: /architecture
    icon: "🏗️"
    description: "System design, data flow, and two-container deployment topology."
  - title: "API Reference"
    url: /api-reference
    icon: "🔌"
    description: "REST endpoints, authentication, and request/response examples."
  - title: "Alert Configuration"
    url: /alerts
    icon: "🔔"
    description: "Webhook, Gotify, ntfy, and Apprise notification setup."
  - title: "Security Guide"
    url: /security
    icon: "🔐"
    description: "API key auth, rate limiting, SSRF protection, and best practices."
  - title: "Runbook"
    url: /runbook
    icon: "📖"
    description: "Operational guide for diagnosing and resolving production issues."
---

## Quick Start

```bash
# Pull and configure
curl -o docker-compose.yml https://raw.githubusercontent.com/fabell4/hermes/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/fabell4/hermes/main/.env.example

# Start containers
docker compose up -d

# Access the UI
open http://localhost:8080
```

---

## Key Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `SPEEDTEST_INTERVAL_MINUTES` | `60` | How often to run speed tests |
| `ENABLED_EXPORTERS` | `csv` | Comma-separated: `csv`, `sqlite`, `prometheus`, `loki` |
| `API_KEY` | *(unset)* | Enables authentication when set |
| `ALERT_FAILURE_THRESHOLD` | `0` | Consecutive failures before alerting (0 = disabled) |
| `PROMETHEUS_PORT` | `8000` | Port for `/metrics` scrape endpoint |
| `LOKI_URL` | *(unset)* | Loki push URL, e.g., `http://loki:3100` |

See [Getting Started](/getting-started) for the full environment variable reference.

---

## Architecture at a Glance

Hermes runs as two containers:

- **hermes-scheduler** — Background worker running speed tests on schedule, exposing Prometheus metrics on port `8000`
- **hermes-api** — FastAPI backend + React frontend on port `8080`

Data flows from the scheduler through exporters (CSV, SQLite, Prometheus, Loki) and is consumed by the frontend via the REST API.
