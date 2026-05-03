# Changelog

<!-- markdownlint-disable MD024 -- Duplicate headings are expected in changelogs for version sections -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

---

## [0.4.3.17-beta] - 2026-05-03

### Chore

- **GHCR** — Re-push to connect the container package to the public repository after repo recreation.

---

## [0.4.3.16-beta] - 2026-05-03

### Fixed

- **Release pipeline** — Public repo push was blocked by GitHub repository rulesets (not classic branch protection). Switched from `DELETE /branches/main/protection` to enumerating and deleting all rulesets via `GET /repos/.../rulesets` + `DELETE /repos/.../rulesets/{id}` before the force-push.

---

## [0.4.3.15-beta] - 2026-05-03

### Fixed

- **Release pipeline** — Eliminated the `releases/vX.Y.Z` branch on the public GitHub repo that was auto-triggering a blocked PR on every release. Sanitized code is now pushed directly to `main` on the public repo (which is a CI-managed mirror). Branch protection on `main` is removed by the CI before pushing. GitHub Pages source updated from `releases/${TAG}/docs` to `main/docs`.

---

## [0.4.3.14-beta] - 2026-05-03

### Fixed

- **Release pipeline** — GHCR package was not appearing in the repo's Packages section because GHCR defaults new packages to private. Added a post-push step that calls `PATCH /user/packages/container/hermes` to set visibility to public. Also ensured the `org.opencontainers.image.source` label is set dynamically at build time (correct repo case) and fixed the Dockerfile static label to use `Hermes` (capital H).

---

## [0.4.3.13-beta] - 2026-05-03

### Fixed

- **Release pipeline** — "Update GitHub Pages source" step no longer fails the job when GitHub Pages is not yet enabled on the public repository (added `continue-on-error: true`).

---

## [0.4.3.12-beta] - 2026-05-03

### Chore

- **Public repository** — Deleted and re-initialized the public GitHub repository; pushed fresh release to re-establish the `Hermes-public` remote and re-enable GitHub Pages.

---

## [0.4.3.11-beta] - 2026-05-03

### Fixed

- **Docs** — Added `repository` key to `docs/_config.yml` to resolve the `jekyll-github-metadata` plugin error during the Jekyll build validation step.

---

## [0.4.3.10-beta] - 2026-05-03

### Fixed

- **Release pipeline** — Jekyll validation kept failing on missing gems (`jekyll-github-metadata`,
  `jekyll-relative-links`). Replaced the ad-hoc `gem install` list with a `docs/Gemfile` so
  bundler resolves all plugin dependencies. Workflow now runs `bundle install && bundle exec jekyll build`.

---

## [0.4.3.9-beta] - 2026-05-03

### Fixed

- **Release pipeline** — Jekyll validation step failed because `jekyll-theme-hacker` gem was
  not installed alongside Jekyll. Added explicit `gem install jekyll-theme-hacker` to the
  validate job so the theme is available during the docs build check.

---

## [0.4.3.8-beta] - 2026-05-03

### Changed

- **Release pipeline** — Consolidated into three explicit blocking jobs (`validate` →
  `build-and-push` → `publish-public`). All quality and security gates (ruff, bandit,
  pip-audit, pytest, Jekyll docs build) now run in `validate` and abort the pipeline before
  any image is built or code reaches the public repo if they fail.
- **Release pipeline** — Jekyll docs build validation added as a pre-publish gate; a broken
  `_config.yml` or theme reference will now block the release rather than silently deploying
  a broken Pages site.
- **Release pipeline** — GitHub Pages source branch is now updated automatically to
  `releases/<tag>` at the end of each release, ensuring the published docs always reflect
  the latest release.
- **Release pipeline** — Removed redundant `ghcr-publish.yml` GitHub Actions workflow;
  Forgejo's `release.yml` owns the full build and publish lifecycle.
- **GitHub CI** — `ci.yml` now also triggers on `releases/**` branches so the sanitized
  public release code is validated on the GitHub side after each push.

---

## [0.4.3.7-beta] - 2026-05-03

### Fixed

- **GitHub Pages** — Jekyll theme was not being applied because `baseurl` in `docs/_config.yml`
  was set to `/hermes` (lowercase) while the repository is served at `/Hermes` (capital H).
  GitHub Pages path resolution is case-sensitive, causing theme CSS/JS assets to 404.

---

## [0.4.3.6-beta] - 2026-05-02

### Fixed

- **Release pipeline** — Pushing sanitized code to `main` on the public GitHub repo is blocked
  by branch protection rules (no force-push, required GPG-signed commits, required GitHub Pages
  status check). Changed the push target from `refs/heads/main` to `refs/heads/releases/<tag>`,
  which is unprotected. The GitHub Release is driven by the tag push, not the branch.

---

## [0.4.3.5-beta] - 2026-05-02

### Fixed

- **Release pipeline** — `pip-audit` creates an internal virtual environment for dependency
  resolution, which failed because `ensurepip`/`venv` was not available on the runner.
  Now installs `python3-full` (via apt) alongside `python3-pip`, which provides the required
  venv support on Debian bookworm.

---

## [0.4.3.4-beta] - 2026-05-02

### Fixed

- **Release pipeline** — Debian bookworm enforces PEP 668 (externally-managed-environment),
  blocking `pip install` system-wide. Added `--break-system-packages` to the `pip install`
  invocation; safe because the security gate runs in a throwaway CI container.

---

## [0.4.3.3-beta] - 2026-05-02

### Fixed

- **Release pipeline** — Security gate pip bootstrap now runs `apt-get update` before attempting
  `apt-get install python3-pip` (stale package lists caused "Unable to locate package" on
  `gft-ci-runner`). Added `get-pip.py` as a final fallback so the gate can never silently skip
  installation and proceed with a broken `pip`.

---

## [0.4.3.2-beta] - 2026-05-02

### Fixed

- **Release pipeline** — `gft-ci-runner` has no `pip` module at all; bootstrap it via
  `python3 -m ensurepip` (falling back to `apt-get install python3-pip`) before installing
  pip-audit in the security gate step.

---

## [0.4.3.1-beta] - 2026-05-02

### Fixed

- **Release pipeline** — Security gate step in `release.yml` used bare `pip` which is absent in
  `gft-ci-runner`; corrected to `python3 -m pip`. Gate also moved before image build/push so
  vulnerabilities block the release before anything is published.

---

## [0.4.3] - 2026-05-02

### Security

- **CVE-2025-54121 (starlette)** — Upgrade `fastapi` 0.115.14 → 0.136.1 and pin `starlette==1.0.0`
  to resolve two starlette vulnerabilities. The previous `fastapi` version capped starlette at
  `<0.47.0`, leaving the transitive dependency on vulnerable 0.46.2.
- **CVE-2025-62727 (starlette)** — Fixed by the same starlette upgrade above (fix available in 0.49.1).

### Fixed

- **Forgejo CI — trivy-deps job** — Added trivy installation step to the `trivy-deps` CI job.
  Trivy is no longer present in the `gft-ci-runner` base image; the job now installs it at
  runtime using the official install script.

---

## [0.4.2] - 2026-05-02

### Fixed

- **GitHub Pages build** — wrap Loki f-string JSON example in `{% raw %}` / `{% endraw %}` tags to
  prevent Jekyll/Liquid from parsing `{{` / `}}` as template variables.
- **Docs lint** — fix markdownlint MD013, MD031, and MD036 errors in
  `PERFORMANCE-OPTIMIZATION-REVIEW.md`.

---

## [0.4.1] - 2026-05-02

### Fixed

- **Alert manager race condition on Linux** — `_wait_for_pending_alerts()` now waits on the
  specific `Future` objects returned by `executor.submit()` rather than a sentinel no-op task.
  The previous approach could complete before alert tasks finished on Linux due to the thread
  pool having multiple available workers, causing intermittent CI test failures.

---

## [0.4.0-beta] - 2026-05-01

### Added

- **Security policy** — Added [SECURITY.md](SECURITY.md) with vulnerability disclosure process,
  supported versions, and coordinated disclosure policy for security researchers
- **Official Ookla CLI integration** — Migrated from unofficial Python `speedtest-cli` library to
  official Ookla speedtest CLI binary for improved reliability and official support
- **Security audit and enhancements** — Comprehensive security review completed with all critical
  issues addressed:
  - API key length validation (32-character minimum enforced at startup)
  - SSRF protection for alert URLs (blocks localhost, private IPs, link-local, non-HTTP schemes)
  - Request body size limit middleware (1 MB default, configurable via `MAX_REQUEST_BODY_SIZE`)
  - Configurable CORS origins (via `CORS_ORIGINS` environment variable)
  - Test alert rate limiting (10-second cooldown with `Retry-After` header)
  - Additional security headers (`X-Frame-Options: DENY`, `Referrer-Policy:
    strict-origin-when-cross-origin`)
  - `Retry-After` header on rate limit responses (429 status)
- **Security documentation** — Added comprehensive security audit report
  ([docs/SECURITY-AUDIT.md](docs/SECURITY-AUDIT.md)) and implementation summary
  ([docs/SECURITY-ENHANCEMENTS.md](docs/SECURITY-ENHANCEMENTS.md))
- **Security test coverage** — 130 API tests including 15 SSRF protection tests, 6 request size
  limit tests, and 7 test alert rate limiting tests
- **Defensive coding improvements** — Comprehensive defensive coding review completed with **all
  15 fixes implemented** (4 high + 7 medium + 4 low priority):
  - Runtime config validation with schema enforcement and type checking (#2)
  - Speed result validation with safe integer/float handling (#4)
  - Thread-safe shared state access for AlertManager (#3)
  - Enhanced failure logging for speedtest errors (#5)
  - Atomic CSV file operations with proper error handling (#7)
  - Alert provider URL validation (HTTP/HTTPS enforcement) (#9)
  - SQLite lock timeout configuration (30 seconds) (#10)
  - Better Prometheus error handling with graceful degradation (#11)
  - Loki exporter URL validation with hostname and timeout checks (#12)
  - Alert manager upper bounds (max 100 failures, max 1 week cooldown) (#13)
  - Config rate limit validation (clamp negative values to 0) (#14)
  - Runtime config interval bounds validation (1-10080 minutes) (#15)
- **Code quality improvements** — Best practices review completed with 5 high/medium priority
  enhancements:
  - Alert provider factory module (`src/services/alert_provider_factory.py`) eliminates ~150
    lines of code duplication
  - Standardized type hints to Python 3.10+ style (`str | None` instead of `Optional[str]`)
  - Constants module (`src/constants.py`) centralizes exporter and provider names
  - Config fallback helper function (`_get_config_value()`) simplifies configuration retrieval
    patterns
  - PEP 8 import organization (Standard library → Third-party → Local) applied across all
    modules
- **Performance optimizations** — Performance optimization review completed with 3 high priority
  improvements:
  - SQLite timestamp index (`idx_results_timestamp DESC`) for 10-100× faster pagination queries
  - Asynchronous alert sending with ThreadPoolExecutor (3 workers) to prevent blocking speedtest
    runs
  - Static file middleware ordering to bypass middleware for asset serving (20% faster page
    loads)
- **Quality assurance documentation** — Added comprehensive review reports:
  - [docs/DEFENSIVE-CODING-REVIEW.md](docs/DEFENSIVE-CODING-REVIEW.md) — 15 issues analyzed, **15
    implemented**
  - [docs/BEST-PRACTICES-REVIEW.md](docs/BEST-PRACTICES-REVIEW.md) — 13 issues analyzed, 5
    implemented
  - [docs/PERFORMANCE-OPTIMIZATION-REVIEW.md](docs/PERFORMANCE-OPTIMIZATION-REVIEW.md) — 9 issues
    analyzed, 3 implemented
  - [docs/DOCUMENTATION-ACCURACY-REVIEW.md](docs/DOCUMENTATION-ACCURACY-REVIEW.md) — 6 HIGH + 3
    LOW priority issues, **all 9 implemented**
- **Expanded test coverage** — Implemented deferred test coverage items from v1.1 roadmap:
  - Alert provider network failure scenarios (6 tests) — multi-provider failures, partial success,
    different exception types
  - API main uncovered lines (12 tests) — SPA fallback and security headers middleware coverage
  - SQLite migration idempotency (7 tests) — fresh init, idempotent re-init, missing column/index
    addition, concurrent migration safety
  - Main loop tests (19 tests) — `build_alert_manager`, `update_alert_providers`,
    `_build_health_status`, `_handle_scheduler_pause_toggle`, `_validate_loki_endpoint`,
    `_validate_environment`, and `main()` startup restore
  - Integration tests — end-to-end flows for speedtest→CSV/SQLite export, multi-exporter
    dispatch, alert lifecycle, cooldown, runtime config persistence
  - Runtime config edge cases (13 tests) — validation, cache behaviour, defense-in-depth paths
  - Alert provider error paths (10 tests) — URL validation, timeout rejection, auth token, apprise
    stateless mode, request error propagation
  - Config module tests (18 tests) — `_get_int`, `_get_bool`, `_get_csv_list`, `_get_str`
    helpers and API_KEY validation via subprocess
  - Alert manager sync fallback (2 tests) — synchronous executor fallback path and timeout logging
  - Frontend component tests — Layout, Dashboard, and Settings page tests
    (`frontend/src/test/Layout.test.tsx`, `Dashboard.test.tsx`, `Settings.test.tsx`)
  - **Test suite: 403 → 497 tests (+94 tests); coverage 92.32% → 96.16%**
  - **All 497 Python tests passing, all 44 frontend tests passing**

### Changed

- **Code organization** — Provider registration logic now shared between scheduler and API
  processes via factory pattern
- **Type system** — All modules use modern Python 3.10+ union syntax consistently
- **Speedtest implementation** — Replaced Python `speedtest-cli` package with official Ookla CLI
  binary invoked via subprocess for better reliability and official API support
- **Test portability** — Subprocess tests in `test_config.py` now use a portable `Path`-derived
  `cwd` instead of a hardcoded Windows path, fixing CI failures on Linux runners

### Fixed

- **Code quality** — Maintained 96.16% coverage (497 tests passing) after refactoring and all
  defensive improvements
- **Apprise provider initialization** — `APPRISE_CONFIG` environment variable now properly
  utilized in `register_apprise_provider()`
- **Duplicate test name** — Renamed duplicate `test_apprise_provider_raises_on_request_error` in
  `test_alert_providers.py` to prevent ruff F811 error

### Removed

- **Deprecated dependency** — Removed unofficial Python `speedtest-cli` package from
  requirements.txt
- **Type suppressions** — Removed mypy type ignore comments for speedtest-cli library (no longer
  needed with CLI-based implementation)

### Security

- **CRITICAL: SSRF vulnerability fixed** — Alert URL validation now prevents attackers from
  targeting internal services, cloud metadata endpoints, or private network infrastructure
- **Enhanced API authentication** — API keys now validated for minimum length (32 characters) on
  startup; application exits with a helpful error message if the key is too short
- **Defense-in-depth improvements** — Multiple security layers now protect production deployments
  (authentication + rate limiting + size limits + SSRF protection + security headers)

---

## [0.3.13-beta] - 2026-04-29

### Fixed

- **GHCR authentication** — use GH_PAT instead of GITHUB_TOKEN for container registry push

---

## [0.3.12-beta] - 2026-04-29

### Fixed

- **GitHub publish workflow** — added `contents:write` permission and release creation steps to
  fix permission errors

---

## [0.3.11-beta] - 2026-04-29

### Fixed

- **CI ZAP job** — added cleanup step to remove leftover containers from previous failed runs

---

## [0.3.10-beta] - 2026-04-29

### Fixed

- **CI workflows** — added Docker Hub authentication to prevent rate limit errors when pulling
  base images

---

## [0.3.9-beta] - 2026-04-29

### Fixed

- **Dockerfile base image** — changed from private registry to public Docker Hub
  `python:3.13-slim` for GitHub Actions compatibility

---

## [0.3.8-beta] - 2026-04-29

### Fixed

- **AppriseProvider type hint** — added explicit `dict[str, Any]` type hint to payload variable
  to allow list[str] assignment for urls field

---

## [0.3.7-beta] - 2026-04-25

### Fixed

- Added setuptools to requirements.txt for Python 3.13 compatibility (semgrep dependency)

---

## [0.3.6-beta] - 2026-04-25

### Fixed

- **health_server log_message signature** — corrected method signature to match
  BaseHTTPRequestHandler parent class (format parameter was missing)
- **ruff formatting** — applied code formatting to speedtest_runner.py

---

## [0.3.5-beta] - 2026-04-24

### Fixed

- **SonarQube Quality Gate** — removed unused type: ignore comments flagged by code quality
  analysis
- **mypy configuration** — refined mypy.ini to properly handle untyped third-party libraries
  without false positives
- **runtime_config type safety** — added explicit cast for json.load() return value

---

## [0.3.4-beta] - 2026-04-24

### Fixed

- **mypy configuration** — added mypy.ini to allow untyped imports from third-party packages
  without type stubs (fixes APScheduler import errors in CI)

---

## [0.3.3-beta] - 2026-04-24

### Fixed

- **pytest-cov version** — corrected from non-existent 6.1.2 to 6.0.0

---

## [0.3.2-beta] - 2026-04-24

### Fixed

- **CI dependencies** — added mypy, pytest-cov, bandit, and semgrep to requirements.txt
  (required by GitHub Actions CI workflow)

---

## [0.3.1-beta] - 2026-04-24

### Changed

- **README.md** — updated release status from alpha to beta, removed all Streamlit UI references
  (deprecated in v0.3.0)
- **Project structure documentation** — corrected file paths (log_service.py), added frontend/ and
  api/ directory structure
- **Frontend package.json** — version synced to 0.3.1 to match project release
- **.env.example** — enabled API_KEY and RATE_LIMIT_PER_MINUTE by default (uncommented) to reflect
  standard feature status

---

## [0.3.0-beta] - 2026-04-23

### Added

- **React + Vite frontend** — modern SPA with Tailwind CSS, Framer Motion animations, and
  TypeScript
- **FastAPI REST API** — replaces file-based IPC with proper HTTP endpoints for triggering tests,
  reading results, and managing configuration
- **Two-container architecture** — `hermes-scheduler` (background worker) and `hermes-api` (REST +
  React frontend) for better separation of concerns
- **API authentication** — optional `API_KEY` environment variable protects write endpoints (`POST
  /api/trigger`, `PUT /api/config`)
- **Rate limiting** — per-API-key rate limiting with configurable `RATE_LIMIT_PER_MINUTE`
  (default: 60 requests/minute)
- **Visual test indicator** — React UI shows "Test Running" badge when a speed test is in progress
  (detects both manual and scheduler-triggered tests)
- **Real-time test status polling** — `GET /api/trigger/status` endpoint allows UI to detect when
  tests are running
- **Automatic result refresh** — UI automatically refreshes data when a test completes
- **Timezone configuration** — `TZ` environment variable controls log timestamps inside containers
  (default: UTC)
- **Data retention policies** — configurable `CSV_MAX_ROWS`, `CSV_RETENTION_DAYS`,
  `SQLITE_MAX_ROWS`, `SQLITE_RETENTION_DAYS` for automatic cleanup
- **Animated speed gauges** — React UI shows randomized values during test execution for visual
  feedback
- **Countdown timer** — displays time until next scheduled test in React UI
- **Vitest test suite** — frontend unit tests with 100% coverage of critical components

### Changed

- **Primary UI** is now React + FastAPI on port `:8080` (Streamlit remains available but is
  considered legacy)
- **Docker compose structure** — `hermes-ui` container renamed to `hermes-api` and serves FastAPI
  - React instead of Streamlit
- **API results endpoint** — returns paginated results from SQLite with fallback to CSV when
  database doesn't exist yet
- **Improved error handling** — 503 status with helpful message when database doesn't exist,
  authentication errors shown to user
- **Environment variable structure** — added `API_PORT` for docker-compose host port binding,
  removed `HEALTH_PORT` (health endpoint is part of FastAPI)

### Fixed

- **Database initialization** — SQLite exporter must be enabled in `ENABLED_EXPORTERS` for
  database to be created
- **Test result freshness** — results refresh immediately after test completion instead of relying
  on 10-second polling interval
- **Race condition in test triggering** — simplified polling logic to avoid conflicts between
  manual trigger and status polling

### Deprecated

- **Streamlit UI** (`src/streamlit_app.py`) — still functional but deprecated in favor of React
  frontend

---

## [0.2.3-alpha] - 2026-04-12

### Fixed

- **Docker user home directory** — changed `useradd --no-create-home` to `useradd --create-home`
  in Dockerfile; Streamlit needs write access to `/home/hermes` for its metrics ID file, absence
  of home directory caused `PermissionError` at container startup
- **Streamlit fragment rerun** — `StreamlitAPIException` when calling `st.rerun(scope="fragment")`
  during a full-page render; `_poll_trigger_state()` now returns the required scope string and the
  `@st.fragment` caller invokes `st.rerun()` — ensuring the call is always made inside a fragment
  context
- **Streamlit redundant rerun** — redundant `st.rerun()` in the "Run Now" button handler triggered
  a full-page render before polling began, causing the `StreamlitAPIException` on the following
  cycle; removed the call since the polling loop calls `st.rerun()` internally
- **Streamlit UI flicker** — whole-UI heartbeat/flicker during manual test polling replaced with
  `st.rerun(scope="fragment")` scoped to the Run Test section only
- **Streamlit result display** — test result metrics (download / upload / ping) not displayed
  after run completion; result now stored in `session_state["last_result"]` before the full-page
  rerun so it survives the transition

### Removed

- **Legacy Flask stub** — `src/web/` directory (`app.py`, `templates/index.html`) superseded by
  the Streamlit UI; Flask was never listed as a dependency

---

## [0.2.2-alpha] - 2026-04-11

### Fixed

- **Streamlit duplicate rendering** — duplicate chart and raw data expander rendered after a
  manual run or schedule save due to `st.rerun()` interrupting mid-script rendering; sections now
  use `@st.fragment` so reruns are scoped and the History section's position in the element tree
  stays stable
- **Streamlit scroll position** — page scrolled to Schedule section on refresh; replaced
  `components.html()` scroll-to-top with `st.html()` targeting the stable
  `data-testid="stAppViewContainer"` attribute and disabling browser scroll restoration

---

## [0.2.1-alpha] - 2026-04-10

### Fixed

- **Release workflow** — correct GitHub repo URL casing (`Hermes.git`) to match repository rename
- **Release workflow** — delete existing GitHub tag via API before pushing to avoid protected-ref
  rejection
- **Release workflow** — delete existing Forgejo release before recreating for idempotent re-runs
- **Release scripts** — use `os.open` with mode `0o600` for temp file writes (SonarQube S5443)
- **Release scripts** — replace hardcoded `/tmp/` paths with `tempfile.gettempdir()`

---

## [0.2.0-alpha] - 2026-04-10

### Added

- `runtime_config.py` — `mark_running()`, `mark_done()`, `is_running()` sentinel file IPC between
  containers
- **"Run Now" UI feedback** — live running indicator and metric cards (download, upload, ping)
  shown after test completes
- **OCI image label** — (`org.opencontainers.image.source`) in Dockerfile linking image to GitHub
  repo

### Changed

- **Scheduler** now runs as a dedicated `hermes-scheduler` container, independent of the Streamlit
  UI
- **Single-image architecture** — Both containers are built from the same image;
  `hermes-scheduler` overrides the entrypoint to run `src.main`
- **UI scheduler communication** — UI no longer owns the APScheduler instance; it communicates
  with the scheduler via shared volume files
- **"Run Now" button** writes a trigger file (`data/.run_trigger`); the scheduler picks it up
  within 30 seconds
- **Schedule and exporter changes** from the UI are applied by the scheduler within 30 seconds of
  saving
- **Restart policy** — Both containers now use `restart: always` (was `unless-stopped`)
- **Docker compose** — now uses `image: ${HERMES_IMAGE:-...}` instead of `build: .`
- **Timestamps** now use `ZoneInfo(TZ)` respecting the container `TZ` environment variable
- **UI timestamp display** converted to local time and stripped of UTC offset for correct
  Streamlit rendering

### Fixed

- **Scheduler persistence** — Scheduler no longer stops after a server reboot; `hermes-scheduler`
  starts eagerly on container start without requiring a UI page visit
- **Error message** from a failed "Run Now" now clears immediately when the button is clicked
  again
- **Stale sentinel** — Stale `.running` sentinel cleared on scheduler startup to recover from
  crash/restart
- **Duplicate dependency** — Duplicate `tzdata` entry in `requirements.txt` causing CI pip install
  conflict

---

## [0.1.0-alpha] - 2026-03-02

### Added

- `SpeedtestRunner` — runs speedtest-cli and returns a typed `SpeedResult`
- `ResultDispatcher` — fan-out hub that dispatches results to one or more exporters
- `CSVExporter` — appends results to a rotating CSV log file
- `PrometheusExporter` — exposes a Prometheus-compatible `/metrics` HTTP endpoint
- `LokiExporter` — ships structured log events via HTTP push to a Loki instance
- `runtime_config.py` — JSON persistence for scheduler interval and enabled exporters, survives
  container restarts via Docker volume
- Streamlit UI — trigger manual runs, view history chart, adjust schedule interval, toggle exporters
- `Dockerfile` and `docker-compose.yml` with named volumes for log and config persistence
- CI pipeline — ruff, mypy, bandit, semgrep, pytest with 80% coverage gate
- Release workflow — builds and pushes Docker image to private registry and GHCR, creates GitHub and Forgejo releases
