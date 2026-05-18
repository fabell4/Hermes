---
layout: default
title: "Grafana Alloy Integration"
---

# Grafana Alloy Integration

Hermes ships a ready-to-use [Grafana Alloy](https://grafana.com/docs/alloy/latest/) configuration
that replaces a hand-rolled Prometheus scrape config + Promtail setup with a single, self-contained
agent.

Alloy handles two responsibilities:

| Pipeline | Source | Destination |
| --- | --- | --- |
| **Metrics** | `hermes-scheduler:8000/metrics` (Prometheus endpoint) | Prometheus / Mimir / Grafana Cloud |
| **Logs** | `hermes-scheduler` and `hermes-api` container stdout/stderr | Loki / Grafana Cloud |

> **Note:** The Loki exporter built into Hermes pushes structured speedtest *results* directly to
> Loki as JSON log lines. Alloy's log pipeline collects the containers' application *log output*
> (startup messages, warnings, error tracebacks, etc.) — the two pipelines are complementary and can
> run simultaneously.

---

## Prerequisites

- Docker Compose v2.20+ (profile support required)
- A running Prometheus-compatible metrics backend (Prometheus, Mimir, or Grafana Cloud)
- A running Loki instance (or Grafana Cloud Loki endpoint)

---

## Deployment Modes

Hermes supports three independent shipping configurations. All local exporters (CSV, SQLite) work
identically in every mode.

### Mode 1 — Direct push (no Alloy)

Hermes pushes directly to Prometheus (via the scrape endpoint) and Loki (via the built-in
`LokiExporter`). No additional infrastructure is required.

**Best for:** Simple setups, or environments where you control the Prometheus scrape target.

```bash
# .env
ENABLED_EXPORTERS=csv,sqlite,prometheus,loki
LOKI_URL=http://loki:3100
```

```bash
docker compose up -d
```

Loki receives one structured JSON event per speedtest run — queryable with:

```logql
{job="hermes_speedtest"} | json | download_mbps > 0
```

---

### Mode 2 — Alloy as sole shipper

Alloy handles all metric and log shipping. Remove `loki` from `ENABLED_EXPORTERS` to avoid
Hermes making its own Loki connections. Enable `LOG_FORMAT=json` so Alloy's `loki.process`
pipeline can parse structured fields from the log lines.

**Best for:** Teams already running Grafana Alloy, or wanting a single agent managing all shipping.

```bash
# .env
ENABLED_EXPORTERS=csv,sqlite,prometheus   # loki intentionally excluded
LOG_FORMAT=json
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
```

```bash
docker compose --profile alloy up -d
```

Loki receives all container log lines as structured JSON — queryable with:

```logql
# All log levels
{job="hermes"}

# Errors only (uses the stream label promoted by loki.process)
{job="hermes", level="ERROR"}

# Speedtest completions
{job="hermes"} | json | message =~ "Test complete.*"
```

**Trade-off:** Loki log lines come from stdout and contain the formatted message string. The rich
per-field JSON (download_mbps, upload_mbps, ping_ms, etc.) that `LokiExporter` sends is not
available via this path.

---

### Mode 3 — Both (recommended for full observability)

Hermes pushes structured per-test results directly to Loki via `LokiExporter`, while Alloy
independently collects all application logs (startup, errors, warnings) and ships metrics via
remote_write. The two log streams are distinguished by their `job` label.

**Best for:** Production deployments where you want structured per-test data AND full application
log visibility.

```bash
# .env
ENABLED_EXPORTERS=csv,sqlite,prometheus,loki
LOG_FORMAT=json
LOKI_URL=http://loki:3100
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
```

```bash
docker compose --profile alloy up -d
```

| Loki stream | What it contains |
| --- | --- |
| `{job="hermes_speedtest"}` | Structured per-test result JSON from `LokiExporter` |
| `{job="hermes"}` | All container application logs from Alloy |

---

## Quick Start

### 1. Set environment variables

Add the following to your `.env` file (copy from `.env.example`):

```bash
# Prometheus remote_write endpoint
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write

# Loki push endpoint
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
```

See [Environment Variables](#environment-variables) below for all options.

### 2. Start Hermes with Alloy

```bash
# Start all services including the Alloy agent
docker compose --profile alloy up -d
```

Alloy's UI and self-metrics endpoint will be available at `http://localhost:12345`.

### 3. Verify metrics are arriving

In your Prometheus/Mimir UI, query:

```promql
hermes_download_mbps
```

### 4. Verify logs are arriving

In Grafana's Explore view (Loki datasource), query:

```logql
{job="hermes"}
```

---

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `PROMETHEUS_REMOTE_WRITE_URL` | *(required)* | Full remote_write URL for metric ingestion |
| `LOKI_PUSH_URL` | `http://loki:3100/loki/api/v1/push` | Full Loki push URL for log ingestion |
| `HERMES_METRICS_ADDRESS` | `hermes-scheduler:8000` | `host:port` of the Hermes metrics endpoint |
| `ALLOY_LOG_LEVEL` | `info` | Alloy agent log verbosity: `debug` \| `info` \| `warn` \| `error` |

---

## Backends

### Self-Hosted Stack (Prometheus + Loki + Grafana)

```bash
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
```

Ensure `hermes-alloy` is on the same Docker network as your Prometheus and Loki containers, or
replace the service names with their host/IP addresses.

### Grafana Mimir

```bash
PROMETHEUS_REMOTE_WRITE_URL=http://mimir:9009/api/v1/push
LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push
```

### Grafana Cloud

```bash
PROMETHEUS_REMOTE_WRITE_URL=https://<prometheus-id>.grafana.net/api/prom/push
LOKI_PUSH_URL=https://<loki-id>.grafana.net/loki/api/v1/push
```

For Grafana Cloud, you also need to add credentials to `alloy/config.alloy`. Edit the
`prometheus.remote_write` and `loki.write` blocks to include basic auth:

```alloy
prometheus.remote_write "default" {
  endpoint {
    url = env("PROMETHEUS_REMOTE_WRITE_URL")
    basic_auth {
      username = env("GRAFANA_CLOUD_METRICS_USER")
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}

loki.write "default" {
  endpoint {
    url = env("LOKI_PUSH_URL")
    basic_auth {
      username = env("GRAFANA_CLOUD_LOGS_USER")
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}
```

Then add the corresponding variables to your `.env`:

```bash
GRAFANA_CLOUD_METRICS_USER=123456
GRAFANA_CLOUD_LOGS_USER=789012
GRAFANA_CLOUD_API_KEY=glc_...
```

---

## Metrics Collected

All Prometheus gauges exposed by Hermes at `/metrics`:

| Metric | Description |
| --- | --- |
| `hermes_download_mbps` | Last measured download speed (Mbit/s) |
| `hermes_upload_mbps` | Last measured upload speed (Mbit/s) |
| `hermes_ping_ms` | Last measured latency (ms) |
| `hermes_jitter_ms` | Last measured jitter (ms) |
| `hermes_packet_loss_pct` | Last measured packet loss (%) |
| `hermes_quality_score` | Composite connection quality score (0–100) |
| `hermes_sla_ok` | SLA status: `1` pass / `0` breached / `-1` disabled |

All gauges carry labels `server_name`, `server_location`, and `isp_name` unless
`PROMETHEUS_DISABLE_LABELS=true` is set.

---

## Log Labels

Every log line collected from Hermes containers arrives in Loki with these stream labels:

| Label | Example value | Source |
| --- | --- | --- |
| `job` | `hermes` | Static (set by Alloy relabeling) |
| `container` | `hermes-scheduler` | Docker container name |
| `image` | `ghcr.io/fabell4/hermes:latest` | Docker image reference |

**Example LogQL queries:**

```logql
# All Hermes application logs
{job="hermes"}

# Scheduler logs only
{job="hermes", container="hermes-scheduler"}

# Errors in any Hermes container
{job="hermes"} |= "ERROR"

# Speedtest failures
{job="hermes", container="hermes-scheduler"} |= "Speedtest failed"
```

---

## Managing the Alloy Service

```bash
# Start Hermes + Alloy
docker compose --profile alloy up -d

# Stop Alloy only (keep Hermes running)
docker compose stop hermes-alloy

# Start Alloy only (if Hermes is already running)
docker compose --profile alloy up -d hermes-alloy

# View Alloy logs
docker logs hermes-alloy

# Open Alloy UI (pipeline graph + component debug)
open http://localhost:12345
```

---

## Configuration File

The Alloy config lives at `alloy/config.alloy` in the repository root and is bind-mounted into the
container as read-only. Edit this file to customise scrape intervals, add additional relabeling
rules, or extend the pipeline with extra components.

After editing, reload without a full restart:

```bash
docker compose --profile alloy restart hermes-alloy
```

---

## Troubleshooting

### Alloy starts but no metrics arrive

1. Open the Alloy UI at `http://localhost:12345` and inspect the `prometheus.remote_write.default`
   component for errors.
2. Check that `PROMETHEUS_REMOTE_WRITE_URL` is set correctly and the backend is reachable from
   inside the container.
3. Confirm the `hermes-scheduler` container is running and `/metrics` returns data:

   ```bash
   curl http://localhost:8000/metrics | grep hermes_
   ```

### Alloy starts but no logs arrive

1. In the Alloy UI, inspect `loki.source.docker.hermes_logs` for errors.
2. Confirm the Docker socket is accessible inside the container:

   ```bash
   docker exec hermes-alloy ls -la /var/run/docker.sock
   ```

3. On some Linux hosts, the Alloy container user needs to be in the `docker` group. Add to the
   service definition in `docker-compose.yml`:

   ```yaml
   group_add:
     - "${DOCKER_GID:-999}"
   ```

4. Check `LOKI_PUSH_URL` is correct and the Loki instance is reachable.

### `discovery.docker` finds no containers

The filter matches containers by name. If you renamed the Hermes containers, update the `values`
list in `alloy/config.alloy`:

```alloy
filter {
  name   = "name"
  values = ["your-scheduler-name", "your-api-name"]
}
```
