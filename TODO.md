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
- [x] `Dockerfile` + `docker-compose.yml` — containerised with volume mounts
- [x] `.dockerignore` — optimised Docker build context
- [x] `requirements.txt` — pinned dependencies
- [x] CI pipeline — ruff, mypy, bandit, semgrep, pytest with 95% coverage; Vitest frontend tests; Safety, pip-audit, Trivy, npm-audit supply-chain scans
- [x] Release workflow — builds and pushes to private registry + GHCR, creates GitHub + Forgejo releases
- [x] Renovate — automated dependency PRs (Python, npm, Docker base images) every weekend

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

### Phase 3 — Production Frontend (beta target)

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
>
> ✅ All Phase 1–3 items complete. Ready for beta tagging.

---

## Phase 4 — Alerting & Quality Assurance

_Goal: notify users when something goes wrong and ensure code quality before v1.0._

### Alerting
- [x] Consecutive failure detection — track N consecutive speedtest failures
- [x] Webhook alerting — POST to a configurable URL on consecutive failure
- [x] Gotify / ntfy support — push notification on failure
- [x] Alert cooldown — don't re-alert within a configurable window
- [x] Alert API endpoints — `GET /api/alerts` and `PUT /api/alerts` with authentication
- [x] Alert UI configuration — frontend settings page for alert providers
- [x] Comprehensive alert tests — 48 tests covering providers, manager, and API
- [x] Alert documentation — README and environment variable examples

### Quality Assurance
- [x] Full code review — comprehensive review of all modules before v1.0 release
  - [x] Security audit (authentication, rate limiting, input validation) — **COMPLETE**
    - ✅ Comprehensive 50-page security audit completed (see [docs/SECURITY-AUDIT.md](docs/SECURITY-AUDIT.md))
    - ✅ All high-priority issues fixed: API key validation, SSRF protection, rate limiting headers
    - ✅ All low-priority enhancements implemented: request size limits, configurable CORS, test alert throttling
    - ✅ 130 API tests passing including 15 SSRF tests, 6 request size tests, 7 rate limit tests
    - ✅ Security enhancements documented (see [docs/SECURITY-ENHANCEMENTS.md](docs/SECURITY-ENHANCEMENTS.md))
    - ✅ Approved for v1.0 release
  - [x] Review for defensive coding practices — **COMPLETE**
    - ✅ Comprehensive defensive coding review completed (see [docs/DEFENSIVE-CODING-REVIEW.md](docs/DEFENSIVE-CODING-REVIEW.md))
    - ✅ 15 issues identified (4 high, 7 medium, 4 low priority)
    - ✅ All critical and medium priority fixes **IMPLEMENTED** (8 total):
      - Runtime config validation (#2)
      - Speed result validation (#4)
      - Shared state thread safety (#3)
      - Enhanced failure logging (#5)
      - Atomic CSV file operations (#7)
      - Alert provider URL validation (#9)
      - SQLite lock timeout (#10)
      - Better Prometheus error handling (#11)
    - ✅ All 344 tests passing with defensive improvements
    - ✅ No static analysis errors
    - ✅ Approved for v1.0 release
    - 📋 4 low-priority improvements deferred to post-v1.0
  - [x] Review for best practices, and possible code simplification — **COMPLETE**
    - ✅ Comprehensive best practices review completed (see [docs/BEST-PRACTICES-REVIEW.md](docs/BEST-PRACTICES-REVIEW.md))
    - ✅ 13 issues identified (3 high, 4 medium, 6 low priority)
    - ✅ All HIGH priority improvements **IMPLEMENTED**:
      - Eliminated duplicate provider registration logic (~150 lines) via shared factory
      - Standardized type hints to modern Python 3.10+ style across all modules
      - Extracted magic strings to constants module
    - ✅ **2 additional MEDIUM priority improvements IMPLEMENTED**:
      - Config fallback pattern helper function (_get_config_value)
      - PEP 8 import organization across all modules
    - ✅ All 344 tests passing with improvements
    - ✅ Static analysis clean (mypy, ruff)
    - ✅ Approved for v1.0 release
    - 📋 2 medium (optional/monitor-only) and 6 low-priority improvements deferred to post-v1.0
  - [x] Review for modernization, remediate deprecated items — **COMPLETE**
    - ✅ Comprehensive modernization review completed (see [docs/MODERNIZATION-REVIEW.md](docs/MODERNIZATION-REVIEW.md))
    - ✅ 6 issues identified (2 high, 3 medium, 1 low priority)
    - ✅ **NO DEPRECATED FEATURES FOUND** - codebase already modern
    - ✅ All HIGH priority improvements **IMPLEMENTED**:
      - SQLite connections converted to context managers
      - String constants converted to StrEnum for type safety
    - ✅ All MEDIUM priority improvements **IMPLEMENTED**:
      - Centralized TZ environment variable in config.py
      - Removed dead Log service code
      - Lock usage reviewed (current pattern appropriate, no changes needed)
    - ✅ All 344 tests passing with improvements
    - ✅ Static analysis clean (mypy, ruff)
    - ✅ Code coverage 91.36% (>90% requirement)
    - ✅ Approved for v1.0 release
  - [x] Error handling completeness — **COMPLETE**
    - ✅ Comprehensive error handling review completed (see [docs/ERROR-HANDLING-REVIEW.md](docs/ERROR-HANDLING-REVIEW.md))
    - ✅ 18 issues identified (8 high, 10 medium priority)
    - ✅ All HIGH priority fixes **IMPLEMENTED**:
      - Atomic runtime config writes (prevents corruption)
      - SQLite lock timeout diagnostics (custom exception)
      - CSV prune failure handling (non-fatal)
      - Thread safety in trigger endpoint (lock release on failure)
      - Loki URL validation improvements (specific exception types)
    - ✅ Critical MEDIUM priority performance optimizations **IMPLEMENTED**:
      - Runtime config caching (file modification time)
      - CSV pruning optimization (skip full read when not needed)
    - ✅ All 344 tests passing (90.16% coverage)
    - ✅ Static analysis clean (mypy, ruff)
    - ✅ Approved for v1.0 release
    - 📋 Test coverage gaps (H6-H8) and documentation polish (M1-M4) deferred to v1.1
  - [ ] Test coverage gaps
  - [ ] Documentation accuracy
  - [ ] Performance optimization opportunities

> 🏁 **Beta → Full release gate** — all Phase 4 items must be complete before tagging v1.0.

---

## Testing Backlog

- [x] Exporter integration tests — CSV schema validation, Prometheus metric values, Loki payload shape
- [x] Scheduler persistence tests — simulate restart and verify interval is restored
- [x] SpeedtestRunner retry tests — verify retry behaviour on transient failure


---

## Post-Release Enhancements

_Features planned for after v1.0. Not required for stable release._

### Enhanced Diagnostics (v1.1 candidates)
- [ ] Packet loss tracking — capture and log packet loss percentage from speedtest results
- [ ] Server selection — allow pinning to specific server ID for consistent baseline testing
- [ ] SLA monitoring — define speed thresholds (e.g., "download ≥100 Mbps") and track compliance percentage
- [ ] Connection quality score — aggregate metric combining speed, latency, jitter, and packet loss

### Data & Integration
- [ ] InfluxDB exporter — optional time-series exporter; pairs with Grafana for long-term trend analysis and retention policy management
- [ ] Data export API — bulk export historical data (CSV dump, JSON export for migration/backup)
- [ ] Result annotations — add notes to specific test results (e.g., "ISP maintenance", "router reboot", "storm")

### Testing Improvements
- [ ] Alternative test providers — support fast.com (Netflix), Google speed test, or custom endpoints as backup when Ookla is down
- [ ] IPv4/IPv6 selection — force tests over specific protocol to isolate dual-stack issues
- [ ] Custom test parameters — configure test duration, number of connections, chunk size
- [ ] Multi-server testing — run tests against multiple servers and compare/aggregate results

### Analysis & Insights
- [ ] Result validation — flag suspicious results (impossibly high speeds, timeouts, inconsistent values)
- [ ] Anomaly detection — automatically flag results that deviate significantly from baseline
- [ ] Time-of-day analysis — show average speeds by hour/day to identify congestion patterns
- [ ] Trend analysis — month-over-month comparison, degradation detection
- [ ] Outage detection — detect and log complete connectivity loss (different from slow speeds)

### UI/UX Enhancements
- [ ] Light theme toggle — add light mode option to React UI
- [ ] Result filtering — filter history by date range, speed threshold, server
- [ ] Dashboard customization — choose which metrics to display, rearrange cards
- [ ] Export charts — download charts as PNG/SVG for reports
- [ ] Scheduled test windows — only run tests during specific hours (avoid counting against data caps)

### Security & Infrastructure (Post-v1.0)
- [ ] API key rotation mechanism — support rotating keys without restart, or multiple valid keys
- [ ] Multi-user support — per-user API keys with access control and audit trails
- [ ] Distributed rate limiting — migrate from in-process state to Redis for multi-instance deployments
- [ ] Secrets vault integration — integrate with HashiCorp Vault or similar for production secret management
- [ ] Strict-Transport-Security header — add HSTS header for HTTPS-only deployments

---

## Archived (Deprecated/Superseded)

_Items that were completed but are no longer part of the active codebase._

### Streamlit UI (replaced by React + FastAPI)

- `streamlit_app.py` — original web UI; decommissioned in favor of React frontend
- Scheduler next-run countdown — completed in Streamlit, reimplemented in React
- Version tag in UI — completed in Streamlit, reimplemented in React (Layout.tsx)
- Version update check — completed in Streamlit, reimplemented in React frontend (Layout.tsx)
- Daily/weekly summary stats table — planned for Streamlit but not implemented; may be added to React if needed
- Connection quality score — planned for Streamlit but not implemented; may be added to React if needed
- Historical charts — completed in Streamlit, reimplemented in React dashboard with Recharts
- Result anomaly flagging — planned for Streamlit but not implemented; may be added to React if needed
- Mobile-friendly layout — completed in Streamlit, reimplemented in React with Tailwind responsive design

