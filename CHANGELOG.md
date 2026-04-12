# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
