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

- [x] Retry logic in `SpeedtestRunner` — one retry on transient failure to address potential first-run hangs
- [x] Health check endpoint (`/health`) — returns scheduler status and last successful run timestamp
- [x] Docker `HEALTHCHECK` — use `/health` once endpoint exists
- [x] Environment validation on startup — warn if Loki URL is unreachable when Loki exporter is enabled
- [x] Multi-architecture Docker build — add `linux/arm64` for ARM server / Raspberry Pi support
- [x] Enable/disable automated scans toggle — UI button (default: enabled) that pauses/resumes the scheduler without changing the configured interval

---

## Phase 2 — Data & Observability

_Goal: make historical data more useful and integrate with the wider observability stack._

- [x] SQLite exporter — queryable history, replaces CSV as the primary storage backend
- [x] Log rotation and management — rotate CSV log by size or age, configurable max file size and retention period
- [x] Data retention policy — auto-prune records older than N days (configurable)
- [x] Grafana dashboard JSON — pre-built dashboard for one-click import against Prometheus/Loki
- [x] Jitter tracking — capture jitter from speedtest results when available
- [x] ISP detection — capture ISP name in `SpeedResult` and export it

> 🏁 **Alpha release gate** — all Phase 1–2 items must be complete before tagging an alpha release.

---

## Phase 3 — UI & UX Improvements

_Goal: complete the Streamlit UI improvements, then replace Streamlit with a React + Vite frontend backed by a FastAPI REST layer._

### Phase 3a — Streamlit Polish (pre-beta)

_Superseded by Phase 3b. Streamlit decommissioned — remaining items below were not implemented and are no longer applicable._

- [x] Scheduler next-run countdown — live timer showing time until the next scheduled run
- [x] Version tag in UI — display the running app version in the page header
- [~] Version update check — implemented in React frontend (Layout.tsx) instead of Streamlit
- [~] Daily/weekly summary stats table — superseded; to be added to React frontend if needed
- [~] Connection quality score — superseded; to be added to React frontend if needed
- [~] Historical charts — superseded; React dashboard already has multi-series Recharts chart
- [~] Result anomaly flagging — superseded; to be added to React frontend if needed
- [~] Mobile-friendly layout (Streamlit) — superseded; React frontend is mobile-responsive

### Phase 3b — Production Frontend (beta target)

- [x] REST API layer (FastAPI) — expose run, history, schedule, and exporter endpoints
- [x] React + Vite scaffold — project structure, Tailwind CSS, dark theme baseline
- [x] Dashboard page — stat cards (download, upload, ping) showing latest result
- [x] Performance history chart — interactive multi-series line chart with crosshair tooltip (Recharts)
- [x] Countdown timer + Run Test button — mirrors current Streamlit functionality
- [x] Settings page — schedule interval and exporter toggles
- [x] Version banner — display running version and update notification (GitHub API)
- [x] Mobile-responsive layout
- [x] Remove Streamlit dependency once frontend is live

> 🏁 **Alpha → Beta release gate** — all Phase 1–3 items must be complete before tagging a beta release.

---

## Phase 4 — Alerting

_Goal: notify users when something goes wrong without requiring Grafana._

- [ ] Consecutive failure detection — track N consecutive speedtest failures
- [ ] Webhook alerting — POST to a configurable URL on consecutive failure
- [ ] Gotify / ntfy support — push notification on failure
- [ ] Alert cooldown — don't re-alert within a configurable window

> 🏁 **Beta → Full release gate** — all Phase 1–4 items must be complete before tagging v1.0.

---

## Testing Backlog

- [ ] Exporter integration tests — CSV schema validation, Prometheus metric values, Loki payload shape
- [ ] Scheduler persistence tests — simulate restart and verify interval is restored
- [x] SpeedtestRunner retry tests — verify retry behaviour on transient failure

---

## Post-Release Enhancements

_Features planned for after v1.0. Not required for stable release._

- [ ] InfluxDB exporter — optional time-series exporter; pairs with Grafana for long-term trend analysis and retention policy management
