# Hermes TODO

## Hermes MVP

### ✅ Done

- [x] `SpeedResult` — data model
- [x] `SpeedtestRunner` — runs the test
- [x] `BaseExporter` — interface contract
- [x] `ResultDispatcher` — fan-out hub with `clear()`
- [x] `CSVExporter` — first working backend
- [x] `main.py` — entry point with scheduler, `update_schedule()`, `update_exporters()`, `EXPORTER_REGISTRY`
- [x] `src/config.py` — centralized env config including `ENABLED_EXPORTERS`
- [x] `src/runtime_config.py` — JSON persistence for interval and enabled exporters
- [x] `streamlit_app.py` — MVP UI with run button, schedule control, exporter toggles, history table
- [x] `PrometheusExporter` — Gauge metrics (`download`, `upload`, `ping`) with labelnames; HTTP `/metrics` server on `PROMETHEUS_PORT`
- [x] `LokiExporter` — structured log shipping with Loki push payload + runtime registration
- [x] Exporter resilience + test modernization — init failure handling, Loki/unit tests, dispatcher test coverage

### 🔲 Still To Do

- [ ] Real web frontend — replace Streamlit with Flask/FastAPI + proper UI
- [ ] `Dockerfile` + `docker-compose` — containerize with volume mounts for `logs/` and `data/`
- [ ] `.dockerignore` — review/update as needed
- [ ] `requirements.txt` — freeze dependencies for Docker build

### 📌 Suggested Implementation Order

1. `requirements.txt` freeze — lock reproducible builds for local + CI + Docker
2. `Dockerfile` + `docker-compose` — package app/runtime with `logs/` + `data/` mounts
3. `.dockerignore` review — optimize Docker context size and build time
4. Real web frontend (Flask/FastAPI + proper UI) — replace MVP Streamlit once backend/exporters are stable

---

## 🔲 Enhancements

### 🚀 Next Sprint (Top 4 Impact)

- [ ] Health check endpoint (`/health`) with scheduler + last-success status _(M, P1)_
- [ ] SQLite backend exporter for queryable historical data _(L, P1)_
- [ ] Mock speedtest path for CI (fixture `SpeedResult`) _(M, P1)_
- [ ] Multi-architecture Docker build (`linux/amd64`, `linux/arm64`) _(L, P1)_

### Observability & Data Quality

- [ ] Jitter tracking in `SpeedResult` when available from speedtest results _(M, P2)_
- [ ] Result anomaly flagging (e.g., >2 std dev drop) _(M, P2)_
- [ ] Test server tracking in persisted history + UI _(S, P2)_
- [ ] ISP detection capture in results _(S, P2)_

### Reliability

- [ ] Retry logic in `SpeedtestRunner` (retry once on transient failure) _(S, P1)_
- [ ] Health check endpoint (`/health`) with scheduler + last-success status _(M, P1 — tracked in Next Sprint)_
- [ ] Consecutive failure alerting (email/webhook/Slack/Gotify) _(M, P2)_

### Data & History

- [ ] SQLite backend exporter for queryable historical data _(L, P1 — tracked in Next Sprint)_
- [ ] Data retention policy (auto-prune older than N days) _(M, P2)_
- [ ] Export to JSON alongside CSV _(S, P3)_

### UI / UX

- [ ] Scheduler next-run countdown in the UI _(M, P2)_
- [ ] Connection quality score (weighted download/upload/ping) _(M, P2)_
- [ ] Daily/weekly summary stats table (min/max/avg) _(M, P2)_
- [ ] Mobile-friendly layout _(M, P2)_
- [ ] Historical charts (beyond the basic line chart in Streamlit) _(M, P2)_
- [ ] Dark mode support _(S, P3)_

### Deployment & Operations

- [ ] Multi-architecture Docker build (`linux/amd64`, `linux/arm64`) _(L, P1 — tracked in Next Sprint)_
- [ ] Grafana dashboard JSON for one-click import _(M, P2)_
- [ ] Docker `HEALTHCHECK` using `/health` endpoint _(S, P2)_
- [ ] Environment validation on startup (Loki/Prometheus reachability checks) _(M, P2)_

### Testing

- [ ] Mock speedtest path for CI (fixture `SpeedResult`) _(M, P1 — tracked in Next Sprint)_
- [ ] Exporter integration tests (CSV schema, Prometheus metrics, Loki payloads) _(M, P2)_
- [ ] Scheduler persistence tests across simulated restart _(M, P2)_

### Existing Idea

- [ ] Alerting (Grafana alerts on Prometheus metrics) _(L, P3)_
