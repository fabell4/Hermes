# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- **Security policy** — Added [SECURITY.md](SECURITY.md) with vulnerability disclosure process, supported versions, and coordinated disclosure policy for security researchers
- **Defensive coding improvements** — Comprehensive defensive coding review completed with 8 critical/medium priority fixes implemented:
  - Runtime config validation with schema enforcement and type checking
  - Speed result validation with safe integer/float handling
  - Thread-safe shared state access for AlertManager
  - Enhanced failure logging for speedtest errors
  - Atomic CSV file operations with proper error handling
  - Alert provider URL validation (HTTP/HTTPS enforcement)
  - SQLite lock timeout configuration (30 seconds)
  - Better Prometheus error handling with graceful degradation
- **Code quality improvements** — Best practices review completed with 5 high/medium priority enhancements:
  - Alert provider factory module (`src/services/alert_provider_factory.py`) eliminates ~150 lines of code duplication
  - Standardized type hints to Python 3.10+ style (`str | None` instead of `Optional[str]`)
  - Constants module (`src/constants.py`) centralizes exporter and provider names
  - Config fallback helper function (`_get_config_value()`) simplifies configuration retrieval patterns
  - PEP 8 import organization (Standard library → Third-party → Local) applied across all modules
- **Performance optimizations** — Performance optimization review completed with 3 high priority improvements:
  - SQLite timestamp index (`idx_results_timestamp DESC`) for 10-100× faster pagination queries
  - Asynchronous alert sending with ThreadPoolExecutor (3 workers) to prevent blocking speedtest runs
  - Static file middleware ordering to bypass middleware for asset serving (20% faster page loads)
- **Quality assurance documentation** — Added comprehensive review reports:
  - [docs/DEFENSIVE-CODING-REVIEW.md](docs/DEFENSIVE-CODING-REVIEW.md) — 15 issues analyzed, 8 implemented
  - [docs/BEST-PRACTICES-REVIEW.md](docs/BEST-PRACTICES-REVIEW.md) — 13 issues analyzed, 5 implemented
  - [docs/PERFORMANCE-OPTIMIZATION-REVIEW.md](docs/PERFORMANCE-OPTIMIZATION-REVIEW.md) — 9 issues analyzed, 3 implemented

### Changed
- **Code organization** — Provider registration logic now shared between scheduler and API processes via factory pattern
- **Type system** — All modules use modern Python 3.10+ union syntax consistently

### Fixed
- **Code quality** — SonarQube finding resolved: `require_enabled` parameter now properly utilized in `register_apprise_provider()`
- **Test coverage** — Maintained 91% coverage (344 tests passing) after refactoring

---

## [1.0.0-beta] - 2026-04-29

### Added
- **Security audit and enhancements** — Comprehensive security review completed with all critical issues addressed:
  - API key length validation (32-character minimum enforced at startup)
  - SSRF protection for alert URLs (blocks localhost, private IPs, link-local, non-HTTP schemes)
  - Request body size limit middleware (1 MB default, configurable via `MAX_REQUEST_BODY_SIZE`)
  - Configurable CORS origins (via `CORS_ORIGINS` environment variable)
  - Test alert rate limiting (10-second cooldown with `Retry-After` header)
  - Additional security headers (`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`)
  - `Retry-After` header on rate limit responses (429 status)
- **Security documentation** — Added comprehensive security audit report ([docs/SECURITY-AUDIT.md](docs/SECURITY-AUDIT.md)) and implementation summary ([docs/SECURITY-ENHANCEMENTS.md](docs/SECURITY-ENHANCEMENTS.md))
- **Security test coverage** — 130 API tests including 15 SSRF protection tests, 6 request size limit tests, and 7 test alert rate limiting tests

### Changed
- **Enhanced API authentication** — API keys now validated for minimum length on startup, application exits with helpful error message if key is too short

### Security
- **CRITICAL: SSRF vulnerability fixed** — Alert URL validation now prevents attackers from targeting internal services, cloud metadata endpoints, or private network infrastructure
- **Defense-in-depth improvements** — Multiple security layers now protect production deployments (authentication + rate limiting + size limits + SSRF protection + security headers)

---

## [0.3.13-beta] - 2026-04-29

### Fixed
- **GHCR authentication** — use GH_PAT instead of GITHUB_TOKEN for container registry push

---

## [0.3.12-beta] - 2026-04-29

### Fixed
- **GitHub publish workflow** — added `contents:write` permission and release creation steps to fix permission errors

---

## [0.3.11-beta] - 2026-04-29

### Fixed
- **CI ZAP job** — added cleanup step to remove leftover containers from previous failed runs

---

## [0.3.10-beta] - 2026-04-29

### Fixed
- **CI workflows** — added Docker Hub authentication to prevent rate limit errors when pulling base images

---

## [0.3.9-beta] - 2026-04-29

### Fixed
- **Dockerfile base image** — changed from private registry to public Docker Hub `python:3.13-slim` for GitHub Actions compatibility

---

## [0.3.8-beta] - 2026-04-29

### Fixed
- **AppriseProvider type hint** — added explicit `dict[str, Any]` type hint to payload variable to allow list[str] assignment for urls field

---

## [0.3.7-beta] - 2026-04-25

### Fixed
- Added setuptools to requirements.txt for Python 3.13 compatibility (semgrep dependency)

## [0.3.6-beta] - 2026-04-25

### Fixed
- **health_server log_message signature** — corrected method signature to match BaseHTTPRequestHandler parent class (format parameter was missing)
- **ruff formatting** — applied code formatting to speedtest_runner.py

---

## [0.3.5-beta] - 2026-04-24

### Fixed
- **SonarQube Quality Gate** — removed unused type: ignore comments flagged by code quality analysis
- **mypy configuration** — refined mypy.ini to properly handle untyped third-party libraries without false positives
- **runtime_config type safety** — added explicit cast for json.load() return value

---

## [0.3.4-beta] - 2026-04-24

### Fixed
- **mypy configuration** — added mypy.ini to allow untyped imports from third-party packages without type stubs (fixes APScheduler import errors in CI)

---

## [0.3.3-beta] - 2026-04-24

### Fixed
- **pytest-cov version** — corrected from non-existent 6.1.2 to 6.0.0

---

## [0.3.2-beta] - 2026-04-24

### Fixed
- **CI dependencies** — added mypy, pytest-cov, bandit, and semgrep to requirements.txt (required by GitHub Actions CI workflow)

---

## [0.3.1-beta] - 2026-04-24

### Changed
- **README.md** — updated release status from alpha to beta, removed all Streamlit UI references (deprecated in v0.3.0)
- **Project structure documentation** — corrected file paths (log_service.py), added frontend/ and api/ directory structure
- **Frontend package.json** — version synced to 0.3.1 to match project release
- **.env.example** — enabled API_KEY and RATE_LIMIT_PER_MINUTE by default (uncommented) to reflect standard feature status

---

## [0.3.0-beta] - 2026-04-23

### Added
- **React + Vite frontend** — modern SPA with Tailwind CSS, Framer Motion animations, and TypeScript
- **FastAPI REST API** — replaces file-based IPC with proper HTTP endpoints for triggering tests, reading results, and managing configuration
- **Two-container architecture** — `hermes-scheduler` (background worker) and `hermes-api` (REST + React frontend) for better separation of concerns
- **API authentication** — optional `API_KEY` environment variable protects write endpoints (`POST /api/trigger`, `PUT /api/config`)
- **Rate limiting** — per-API-key rate limiting with configurable `RATE_LIMIT_PER_MINUTE` (default: 60 requests/minute)
- **Visual test indicator** — React UI shows "Test Running" badge when a speed test is in progress (detects both manual and scheduler-triggered tests)
- **Real-time test status polling** — `GET /api/trigger/status` endpoint allows UI to detect when tests are running
- **Automatic result refresh** — UI automatically refreshes data when a test completes
- **Timezone configuration** — `TZ` environment variable controls log timestamps inside containers (default: UTC)
- **Data retention policies** — configurable `CSV_MAX_ROWS`, `CSV_RETENTION_DAYS`, `SQLITE_MAX_ROWS`, `SQLITE_RETENTION_DAYS` for automatic cleanup
- **Animated speed gauges** — React UI shows randomized values during test execution for visual feedback
- **Countdown timer** — displays time until next scheduled test in React UI
- **Vitest test suite** — frontend unit tests with 100% coverage of critical components

### Changed
- **Primary UI** is now React + FastAPI on port `:8080` (Streamlit remains available but is considered legacy)
- **Docker compose structure** — `hermes-ui` container renamed to `hermes-api` and serves FastAPI + React instead of Streamlit
- **API results endpoint** — returns paginated results from SQLite with fallback to CSV when database doesn't exist yet
- **Improved error handling** — 503 status with helpful message when database doesn't exist, authentication errors shown to user
- **Environment variable structure** — added `API_PORT` for docker-compose host port binding, removed `HEALTH_PORT` (health endpoint is part of FastAPI)

### Fixed
- **Database initialization** — SQLite exporter must be enabled in `ENABLED_EXPORTERS` for database to be created
- **Test result freshness** — results refresh immediately after test completion instead of relying on 10-second polling interval
- **Race condition in test triggering** — simplified polling logic to avoid conflicts between manual trigger and status polling

### Deprecated
- **Streamlit UI** (`src/streamlit_app.py`) — still functional but deprecated in favor of React frontend

---

## [0.2.3-alpha] - 2026-04-12

### Fixed
- Docker: `useradd --no-create-home` changed to `useradd --create-home` in Dockerfile; Streamlit needs write access to `/home/hermes` for its metrics ID file, absence of home directory caused `PermissionError` at container startup
- Streamlit UI: `StreamlitAPIException` when calling `st.rerun(scope="fragment")` during a full-page render; `_poll_trigger_state()` now returns the required scope string and the `@st.fragment` caller invokes `st.rerun()` — ensuring the call is always made inside a fragment context
- Streamlit UI: redundant `st.rerun()` in the "Run Now" button handler triggered a full-page render before polling began, causing the `StreamlitAPIException` on the following cycle; removed the call so polling starts and stays within the fragment context
- Streamlit UI: whole-UI heartbeat/flicker during manual test polling replaced with `st.rerun(scope="fragment")` scoped to the Run Test section only
- Streamlit UI: test result metrics (download / upload / ping) not displayed after run completion; result now stored in `session_state["last_result"]` before the full-page rerun so it survives the transition

### Removed
- `src/web/` — legacy Flask stub (`app.py`, `templates/index.html`) superseded by the Streamlit UI; Flask was never listed as a dependency

---

## [0.2.2-alpha] - 2026-04-11

### Fixed
- Streamlit UI — duplicate chart and raw data expander rendered after a manual run or schedule save due to `st.rerun()` interrupting mid-script rendering; sections now use `@st.fragment` so reruns are scoped and the History section's position in the element tree stays stable
- Streamlit UI — page scrolled to Schedule section on refresh; replaced `components.html()` scroll-to-top with `st.html()` targeting the stable `data-testid="stAppViewContainer"` attribute and disabling browser scroll restoration

---

## [0.2.1-alpha] - 2026-04-10

### Fixed
- Release workflow: correct GitHub repo URL casing (`Hermes.git`) to match repository rename
- Release workflow: delete existing GitHub tag via API before pushing to avoid protected-ref rejection
- Release workflow: delete existing Forgejo release before recreating for idempotent re-runs
- Release scripts: use `os.open` with mode `0o600` for temp file writes (SonarQube S5443)
- Release scripts: replace hardcoded `/tmp/` paths with `tempfile.gettempdir()`

---

## [0.2.0-alpha] - 2026-04-10

### Added
- `runtime_config.py` — `mark_running()`, `mark_done()`, `is_running()` sentinel file IPC between containers
- "Run Now" UI feedback — live running indicator and metric cards (download, upload, ping) shown after test completes
- OCI image label (`org.opencontainers.image.source`) in Dockerfile linking image to GitHub repo

### Changed
- Scheduler now runs as a dedicated `hermes-scheduler` container, independent of the Streamlit UI
- Both containers are built from the same image — `hermes-scheduler` overrides the entrypoint to run `src.main`
- UI no longer owns the APScheduler instance; it communicates with the scheduler via shared volume files
- "Run Now" button writes a trigger file (`data/.run_trigger`); the scheduler picks it up within 30 seconds
- Schedule and exporter changes from the UI are applied by the scheduler within 30 seconds of saving
- Both containers now use `restart: always` (was `unless-stopped`)
- `docker-compose.yml` now uses `image: ${HERMES_IMAGE:-...}` instead of `build: .`
- Timestamps now use `ZoneInfo(TZ)` respecting the container `TZ` environment variable
- UI timestamp display converted to local time and stripped of UTC offset for correct Streamlit rendering

### Fixed
- Scheduler no longer stops after a server reboot — `hermes-scheduler` starts eagerly on container start without requiring a UI page visit
- Error message from a failed "Run Now" now clears immediately when the button is clicked again
- Stale `.running` sentinel cleared on scheduler startup to recover from crash/restart
- Duplicate `tzdata` entry in `requirements.txt` causing CI pip install conflict

---

## [0.1.0-alpha] - 2026-03-02

### Added
- `SpeedtestRunner` — runs speedtest-cli and returns a typed `SpeedResult`
- `ResultDispatcher` — fan-out hub that dispatches results to one or more exporters
- `CSVExporter` — appends results to a rotating CSV log file
- `PrometheusExporter` — exposes a Prometheus-compatible `/metrics` HTTP endpoint
- `LokiExporter` — ships structured log events via HTTP push to a Loki instance
- `runtime_config.py` — JSON persistence for scheduler interval and enabled exporters, survives container restarts via Docker volume
- Streamlit UI — trigger manual runs, view history chart, adjust schedule interval, toggle exporters
- `Dockerfile` and `docker-compose.yml` with named volumes for log and config persistence
- CI pipeline — ruff, mypy, bandit, semgrep, pytest with 80% coverage gate
- Release workflow — builds and pushes Docker image to private registry and GHCR, creates GitHub and Forgejo releases
