---
layout: default
title: "Grafana Alloy Integration"
---

# Grafana Alloy Integration

`alloy/hermes.alloy` is an importable [Grafana Alloy](https://grafana.com/docs/alloy/latest/)
module that adds Hermes telemetry to your **existing** Alloy deployment.  It does not define its
own remote_write or loki.write endpoints — it wires into the receivers your config already has.

Two independent modules are provided:

| Module | What it does |
| --- | --- |
| `hermes.metrics` | Scrapes the Hermes `/metrics` endpoint and forwards to your `prometheus.remote_write` receiver |
| `hermes.logs` | Tails the Hermes log file (and optionally the systemd journal) and forwards to your `loki.write` receiver |

> **Note:** The Loki exporter built into Hermes pushes structured speedtest *results* directly to
> Loki as JSON log lines. Alloy's log pipeline collects the *application log output* (startup
> messages, warnings, error tracebacks, etc.) — the two streams are complementary and can run
> simultaneously.

---

## Prerequisites

- Grafana Alloy already installed and running (system package, container, or other deployment)
- A `prometheus.remote_write` component already defined in your Alloy config (for metrics)
- A `loki.write` component already defined in your Alloy config (for logs)

---

## Setup

### 1. Copy the module file

```bash
cp alloy/hermes.alloy /etc/alloy/hermes.alloy
```

Adjust the destination to match wherever your Alloy config directory is (e.g.
`/opt/alloy/`, `~/.config/alloy/`).

### 2. Import and instantiate in your existing config

Add the following to your Alloy config file (typically `config.alloy`):

```alloy
import.file "hermes" {
  filename = "/etc/alloy/hermes.alloy"
}

// Metrics — scrapes localhost:8000/metrics every 15 s
hermes.metrics "default" {
  forward_to = [prometheus.remote_write.default.receiver]
}

// Logs — tails the Hermes log file
hermes.logs "default" {
  log_path   = "/opt/hermes/logs/hermes.log"   // adjust to your install path
  forward_to = [loki.write.default.receiver]
}
```

Both modules are independent — include only what you need.

### 3. Reload Alloy

```bash
sudo systemctl reload alloy          # system agent (Linux)
docker compose restart alloy         # if running Alloy in a container
```

---

## Hermes Configuration

With `hermes.alloy` handling log shipping you can remove `loki` from `ENABLED_EXPORTERS`:

```bash
# .env
ENABLED_EXPORTERS=csv,prometheus   # Alloy tails logs; no direct Loki push from Hermes
LOG_FORMAT=json                    # recommended — enables structured field extraction in Alloy
```

Setting `LOG_FORMAT=json` is optional but improves log queryability. The parse pipeline in
`hermes.logs` handles both `json` and `text` formats automatically.

---

## Module Reference

### `hermes.metrics`

Scrapes the Hermes Prometheus `/metrics` endpoint and forwards time-series to one or more
`prometheus.remote_write` receivers.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `forward_to` | yes | — | List of `prometheus.remote_write` receivers |
| `address` | no | `localhost:8000` | `host:port` of the Hermes `/metrics` endpoint. Override when `PROMETHEUS_PORT` is non-default or Hermes runs on a remote host |
| `scrape_interval` | no | `15s` | How often to scrape. Align with your Prometheus/Mimir retention settings |

### `hermes.logs`

Tails the Hermes log file on disk, parses structured fields, and forwards to one or more
`loki.write` (or `loki.process`) receivers. Optionally also reads from the systemd journal.

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `forward_to` | yes | — | List of `loki.write` or `loki.process` receivers |
| `log_path` | yes | — | Absolute path to `hermes.log` on disk |
| `job_label` | no | `hermes` | Value of the Loki `job` stream label |
| `systemd_unit` | no | `""` | Systemd unit name for journal collection. Empty string disables journal collection |

---

## Examples

### Metrics only

```alloy
import.file "hermes" {
  filename = "/etc/alloy/hermes.alloy"
}

hermes.metrics "default" {
  forward_to = [prometheus.remote_write.default.receiver]
}
```

### Custom port and scrape interval

```alloy
hermes.metrics "default" {
  address         = "localhost:9100"
  scrape_interval = "30s"
  forward_to      = [prometheus.remote_write.default.receiver]
}
```

### Logs with systemd journal

```alloy
hermes.logs "default" {
  log_path     = "/var/log/hermes/hermes.log"
  systemd_unit = "hermes"
  forward_to   = [loki.write.default.receiver]
}
```

### Feed logs into an existing processing stage

```alloy
hermes.logs "default" {
  log_path   = "/opt/hermes/logs/hermes.log"
  forward_to = [loki.process.my_pipeline.receiver]
}
```

### Both modules together

```alloy
import.file "hermes" {
  filename = "/etc/alloy/hermes.alloy"
}

hermes.metrics "default" {
  forward_to = [prometheus.remote_write.default.receiver]
}

hermes.logs "default" {
  log_path     = "/opt/hermes/logs/hermes.log"
  systemd_unit = "hermes"
  forward_to   = [loki.write.default.receiver]
}
```

### Grafana Cloud — passing credentials from your existing config

`hermes.alloy` forwards to receivers you already defined, so Grafana Cloud credentials stay in
your existing `prometheus.remote_write` and `loki.write` blocks — no changes to `hermes.alloy`
are needed:

```alloy
// Already in your config:
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

// Just import and wire:
import.file "hermes" { filename = "/etc/alloy/hermes.alloy" }

hermes.metrics "default" { forward_to = [prometheus.remote_write.default.receiver] }
hermes.logs "default" {
  log_path   = "/opt/hermes/logs/hermes.log"
  forward_to = [loki.write.default.receiver]
}
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
`PROMETHEUS_DISABLE_LABELS=true` is set in Hermes.

---

## Log Labels and Queries

Every log line forwarded by `hermes.logs` arrives in Loki with these stream labels:

| Label | Example value | Source |
| --- | --- | --- |
| `job` | `hermes` | `job_label` argument (default `hermes`) |
| `level` | `INFO` | Extracted from log line by the parse pipeline |

**Example LogQL queries:**

```logql
# All Hermes application logs
{job="hermes"}

# Errors only
{job="hermes", level="ERROR"}

# Speedtest completions (requires LOG_FORMAT=json)
{job="hermes"} | json | message =~ "Test complete.*"

# Structured speedtest results (from LokiExporter, not Alloy)
{job="hermes_speedtest"} | json | download_mbps > 0
```

---

## Troubleshooting

### No metrics arriving

1. Open the Alloy UI (`http://<alloy-host>:12345`) and inspect the `prometheus.scrape.hermes`
   component for errors.
2. Confirm Hermes is running and `/metrics` is reachable from the Alloy host:

   ```bash
   curl http://localhost:8000/metrics | grep hermes_
   ```

3. Check the `address` argument matches `PROMETHEUS_PORT` in your Hermes config (default `8000`).

### No logs arriving

1. In the Alloy UI, inspect `loki.source.file.hermes` for errors.
2. Confirm `log_path` points to the correct absolute path and the file exists.
3. The Alloy process user must have read access to the log file.
4. If using `systemd_unit` and seeing journal errors, confirm the unit name is correct and that
   the Alloy user can read the journal (`journalctl -u hermes` should work).  Remove the
   `systemd_unit` argument to disable journal collection if not needed.
