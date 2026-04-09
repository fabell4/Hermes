# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed
- Scheduler now runs as a dedicated `hermes-scheduler` container, independent of the Streamlit UI
- Both containers are built from the same image — `hermes-scheduler` overrides the entrypoint to run `src.main`
- UI no longer owns the APScheduler instance; it communicates with the scheduler via shared volume files
- "Run Now" button writes a trigger file (`data/.run_trigger`); the scheduler picks it up within 30 seconds
- Schedule and exporter changes from the UI are applied by the scheduler within 30 seconds of saving
- Both containers now use `restart: always` (was `unless-stopped`)

### Fixed
- Scheduler no longer stops after a server reboot — `hermes-scheduler` starts eagerly on container start without requiring a UI page visit

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
