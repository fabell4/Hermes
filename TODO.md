# Hermes — Roadmap & TODO

---

## ✅ Completed

- [x] `SpeedResult` — data model
- [x] `SpeedtestRunner` — runs the test
- [x] `BaseExporter` — interface contract
- [x] `ResultDispatcher` — fan-out hub with `clear()`
- [x] `CSVExporter` — file-based result logging
- [x] `PrometheusExporter` — Gauge metrics with `/metrics` HTTP endpoint
- [x] `LokiExporter` — structured log shipping via HTTP push
- [x] `main.py` — entry point with scheduler, `update_schedule()`, `update_exporters()`, `EXPORTER_REGISTRY`
- [x] `config.py` — centralised env config
- [x] `runtime_config.py` — JSON persistence for interval and enabled exporters
- [x] `streamlit_app.py` — UI with run button, schedule control, exporter toggles, history chart
- [x] `Dockerfile` + `docker-compose.yml` — containerised with volume mounts
- [x] `.dockerignore` — optimised Docker build context
- [x] `requirements.txt` — pinned dependencies
- [x] CI pipeline — ruff, mypy, bandit, semgrep, pytest with 80% coverage gate
- [x] Release workflow — builds and pushes to private registry + GHCR, creates GitHub + Forgejo releases

---

## Phase 1 — Stability (post-alpha)

_Goal: make the deployed instance reliable before adding features._

- [ ] Retry logic in `SpeedtestRunner` — one retry on transient failure to address potential first-run hangs
- [ ] Health check endpoint (`/health`) — returns scheduler status and last successful run timestamp
- [ ] Docker `HEALTHCHECK` — use `/health` once endpoint exists
- [ ] Environment validation on startup — warn if Loki URL is unreachable when Loki exporter is enabled
- [ ] Multi-architecture Docker build — add `linux/arm64` for ARM server / Raspberry Pi support
- [ ] Enable/disable automated scans toggle — UI button (default: enabled) that pauses/resumes the scheduler without changing the configured interval

---

## Phase 2 — Data & Observability

_Goal: make historical data more useful and integrate with the wider observability stack._

- [ ] SQLite exporter — queryable history, replaces CSV as the primary storage backend
- [ ] InfluxDB exporter — optional time-series exporter; pairs with Grafana for long-term trend analysis and retention policy management
- [ ] Data retention policy — auto-prune records older than N days (configurable)
- [ ] Grafana dashboard JSON — pre-built dashboard for one-click import against Prometheus/Loki/InfluxDB
- [ ] Jitter tracking — capture jitter from speedtest results when available
- [ ] ISP detection — capture ISP name in `SpeedResult` and export it

---

## Phase 3 — UI & UX Improvements

_Goal: improve the Streamlit UI while it remains the primary frontend._

- [ ] Scheduler next-run countdown
- [ ] Daily/weekly summary stats table (min/max/avg per day)
- [ ] Connection quality score — weighted composite of download/upload/ping
- [ ] Historical charts — per-metric breakdowns, not just the combined line chart
- [ ] Result anomaly flagging — highlight runs >2 std dev from the rolling mean
- [ ] Mobile-friendly layout

---

## Phase 4 — Alerting

_Goal: notify users when something goes wrong without requiring Grafana._

- [ ] Consecutive failure detection — track N consecutive speedtest failures
- [ ] Webhook alerting — POST to a configurable URL on consecutive failure
- [ ] Gotify / ntfy support — push notification on failure
- [ ] Alert cooldown — don't re-alert within a configurable window

---

## Phase 5 — Production Frontend

_Goal: replace Streamlit with a proper web frontend when the backend is stable._

- [ ] REST API layer (FastAPI) — expose run, history, schedule, and exporter endpoints
- [ ] Proper frontend (HTMX or lightweight JS) — replaces Streamlit
- [ ] Dark mode support
- [ ] Remove Streamlit dependency once frontend is live

---

## Testing Backlog

- [ ] Exporter integration tests — CSV schema validation, Prometheus metric values, Loki payload shape
- [ ] Scheduler persistence tests — simulate restart and verify interval is restored
- [ ] SpeedtestRunner retry tests — verify retry behaviour on transient failure
