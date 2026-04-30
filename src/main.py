# main.py
"""
Hermes — entry point.
Wires all components together, starts the scheduler, and runs the application.
"""

from __future__ import annotations

# Standard library
import logging
import sys
import time
from collections.abc import Callable

# Third-party
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Local
from . import config
from . import runtime_config
from . import shared_state
from .constants import (
    EXPORTER_CSV,
    EXPORTER_LOKI,
    EXPORTER_PROMETHEUS,
    EXPORTER_SQLITE,
)
from .exporters.base_exporter import BaseExporter
from .exporters.csv_exporter import CSVExporter
from .exporters.loki_exporter import LokiExporter
from .exporters.prometheus_exporter import PrometheusExporter
from .exporters.sqlite_exporter import SQLiteExporter
from .result_dispatcher import DispatchError, ResultDispatcher
from .runtime_config import set_enabled_exporters, set_interval_minutes
from .services.alert_manager import AlertManager
from .services.alert_provider_factory import register_all_providers
from .services.health_server import HealthServer
from .services.speedtest_runner import SpeedtestRunner

# --- Logging setup ---
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/hermes.log"),
    ],
)
logger = logging.getLogger(__name__)


def _build_loki_exporter() -> LokiExporter:
    if not config.LOKI_URL:
        raise ValueError("LOKI_URL is required when Loki exporter is enabled.")
    return LokiExporter(url=config.LOKI_URL, job_label=config.LOKI_JOB_LABEL)


# All known exporters and how to build them.
# Keys are strings for runtime flexibility (StrEnum values are strings)
EXPORTER_REGISTRY: dict[str, Callable[[], BaseExporter]] = {
    EXPORTER_CSV: lambda: CSVExporter(
        path=config.CSV_LOG_PATH,
        max_rows=config.CSV_MAX_ROWS,
        retention_days=config.CSV_RETENTION_DAYS,
    ),
    EXPORTER_PROMETHEUS: lambda: PrometheusExporter(port=config.PROMETHEUS_PORT),
    EXPORTER_LOKI: _build_loki_exporter,
    EXPORTER_SQLITE: lambda: SQLiteExporter(
        path=config.SQLITE_DB_PATH,
        max_rows=config.SQLITE_MAX_ROWS,
        retention_days=config.SQLITE_RETENTION_DAYS,
    ),
}


def build_dispatcher() -> ResultDispatcher:
    """
    Instantiates and registers exporters based on the enabled list.
    Priority: runtime_config.json → ENABLED_EXPORTERS env var.
    """
    dispatcher = ResultDispatcher()
    enabled = runtime_config.get_enabled_exporters(default=config.ENABLED_EXPORTERS)

    for name in enabled:
        if name in EXPORTER_REGISTRY:
            try:
                dispatcher.add_exporter(name, EXPORTER_REGISTRY[name]())
            except Exception as e:  # pylint: disable=broad-except  # NOSONAR
                logger.warning("Exporter '%s' could not be initialized: %s", name, e)
        else:
            logger.warning("Unknown exporter '%s' in enabled list — skipping.", name)

    return dispatcher


def update_exporters(dispatcher: ResultDispatcher, enabled: list[str]) -> None:
    """
    Updates the active exporters at runtime and persists the change.
    Called by the UI when the user toggles exporters.
    Clears all current exporters and re-registers only the enabled ones.
    """
    dispatcher.clear()

    for name in enabled:
        if name in EXPORTER_REGISTRY:
            try:
                dispatcher.add_exporter(name, EXPORTER_REGISTRY[name]())
            except Exception as e:  # pylint: disable=broad-except  # NOSONAR
                logger.warning("Exporter '%s' could not be initialized: %s", name, e)
        else:
            logger.warning("Unknown exporter '%s' in enabled list — skipping.", name)

    logger.info("Updated enabled exporters: %s", enabled)
    set_enabled_exporters(enabled)


def build_alert_manager() -> AlertManager:
    """
    Instantiates AlertManager and registers alert providers based on configuration.
    Priority: runtime_config.json → environment variables.
    """
    alert_config = runtime_config.get_alert_config()

    # Use runtime config or fall back to environment
    failure_threshold = alert_config.get(
        "failure_threshold", config.ALERT_FAILURE_THRESHOLD
    )
    cooldown_minutes = alert_config.get(
        "cooldown_minutes", config.ALERT_COOLDOWN_MINUTES
    )

    # Create manager (even if disabled, for potential runtime enable)
    manager = AlertManager(
        failure_threshold=max(1, failure_threshold),  # Minimum threshold of 1
        cooldown_minutes=cooldown_minutes,
    )

    # Only register providers if alerting is enabled
    if alert_config.get("enabled", False) or failure_threshold > 0:
        register_all_providers(
            manager,
            alert_config.get("providers", {}),
            require_enabled=False,
        )

    return manager


def update_alert_providers(manager: AlertManager, alert_config: dict) -> None:
    """
    Updates the active alert providers at runtime and persists the change.
    Called by the UI when the user updates alert configuration.
    """
    # Update manager configuration
    if "failure_threshold" in alert_config:
        manager.failure_threshold = max(1, alert_config["failure_threshold"])
    if "cooldown_minutes" in alert_config:
        manager.cooldown_minutes = alert_config["cooldown_minutes"]

    # Clear and re-register providers
    manager.clear_providers()

    if alert_config.get("enabled", False):
        register_all_providers(
            manager,
            alert_config.get("providers", {}),
            require_enabled=False,
        )
        logger.info("Alert providers updated and enabled.")
    else:
        logger.info("Alerting disabled — providers cleared.")

    # Persist configuration
    runtime_config.set_alert_config(alert_config)


def run_once(
    service: SpeedtestRunner,
    dispatcher: ResultDispatcher,
    alert_manager: AlertManager | None = None,
) -> None:
    """
    Runs a single speedtest and dispatches the result to all exporters.
    Called by the scheduler and importable by the Streamlit/web layer.
    """
    runtime_config.mark_running()
    try:
        logger.info("Starting speedtest run...")
        try:
            result = service.run()
            logger.info(
                "Test complete — Down: %sMbps | Up: %sMbps | Ping: %sms | Server: %s",
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
                result.server_name,
            )
            # Record success with alert manager
            if alert_manager:
                alert_manager.record_success()
        except RuntimeError as e:
            logger.error("Speedtest failed: %s", e, exc_info=True)
            # Record failure with alert manager
            if alert_manager:
                alert_manager.record_failure(str(e))

            # In development, make failures more visible
            if config.APP_ENV == "development":
                logger.critical("Speedtest failure in development mode")
            return
        try:
            dispatcher.dispatch(result)
            runtime_config.set_last_run_at(result.timestamp.isoformat())
        except DispatchError as e:
            logger.warning("Dispatch completed with failures:")
            for name, error in e.failures.items():
                logger.warning("  [%s] %s", name, error)
            runtime_config.set_last_run_at(result.timestamp.isoformat())
    finally:
        runtime_config.mark_done()


def build_scheduler(
    service: SpeedtestRunner,
    dispatcher: ResultDispatcher,
    alert_manager: AlertManager | None = None,
) -> BackgroundScheduler:
    """
    Configures and returns the background scheduler.
    Does not start it — caller decides when to start.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: run_once(service, dispatcher, alert_manager),
        trigger=IntervalTrigger(minutes=config.SPEEDTEST_INTERVAL_MINUTES),
        id="speedtest_run",
        name="Scheduled speedtest run",
        max_instances=1,  # Prevent overlapping runs if a test takes longer than the interval
        misfire_grace_time=60,  # If a run is missed by less than 60s, still execute it
    )
    return scheduler


def update_schedule(scheduler: BackgroundScheduler, new_interval_minutes: int) -> None:
    """
    Updates the scheduler interval at runtime and persists it for next startup.
    Called by the UI when the user changes the interval.
    """
    scheduler.reschedule_job(
        job_id="speedtest_run",
        trigger=IntervalTrigger(minutes=new_interval_minutes),
    )
    set_interval_minutes(new_interval_minutes)
    logger.info("Schedule updated — new interval: %s minutes.", new_interval_minutes)


def _poll_once(
    scheduler: BackgroundScheduler,
    dispatcher: ResultDispatcher,
    service: SpeedtestRunner,
    alert_manager: AlertManager,
    last_interval: int,
    last_exporters: list[str],
    last_paused: bool = False,
    last_alert_config: dict | None = None,
    last_next_run_time: str | None = None,
) -> tuple[int, list[str], bool, dict, str | None]:
    """
    Execute one poll cycle — checks runtime_config.json for UI-driven changes
    and reacts accordingly. Returns the (possibly updated) interval, exporters,
    paused state, alert config, and next run time.
    Extracted from the main loop to make it unit-testable.
    """
    if last_alert_config is None:
        last_alert_config = {}

    # --- React to interval changes written by the UI ---
    current_interval = runtime_config.get_interval_minutes(
        default=config.SPEEDTEST_INTERVAL_MINUTES
    )
    if current_interval != last_interval:
        update_schedule(scheduler, current_interval)
        last_interval = current_interval

    # --- React to exporter changes written by the UI ---
    current_exporters = runtime_config.get_enabled_exporters(
        default=config.ENABLED_EXPORTERS
    )
    if sorted(current_exporters) != sorted(last_exporters):
        update_exporters(dispatcher, current_exporters)
        last_exporters = current_exporters

    # --- React to alert configuration changes written by the UI ---
    current_alert_config = runtime_config.get_alert_config()
    if current_alert_config != last_alert_config:
        update_alert_providers(alert_manager, current_alert_config)
        last_alert_config = current_alert_config

    # --- React to "Run Now" trigger written by the UI ---
    if runtime_config.consume_run_trigger():
        logger.info("Run trigger detected — starting immediate test.")
        run_once(service, dispatcher, alert_manager)

    # --- React to pause/resume toggle written by the UI ---
    current_paused = runtime_config.get_scheduler_paused()
    if current_paused != last_paused:
        _handle_scheduler_pause_toggle(scheduler, current_paused)
        last_paused = current_paused

    # --- Persist next run time for the UI countdown (only if changed) ---
    job = scheduler.get_job("speedtest_run")
    current_next_run_time = None
    if job and job.next_run_time:
        current_next_run_time = job.next_run_time.isoformat()
        if current_next_run_time != last_next_run_time:
            runtime_config.set_next_run_at(current_next_run_time)
            last_next_run_time = current_next_run_time

    return (
        last_interval,
        last_exporters,
        last_paused,
        last_alert_config,
        last_next_run_time,
    )


def _handle_scheduler_pause_toggle(
    scheduler: BackgroundScheduler, should_pause: bool
) -> None:
    """Handle pausing or resuming the scheduler job."""
    job = scheduler.get_job("speedtest_run")
    if not job:
        return

    if should_pause:
        scheduler.pause_job("speedtest_run")
        logger.info("Automated scans paused.")
    else:
        scheduler.resume_job("speedtest_run")
        logger.info("Automated scans resumed.")


def _build_health_status(scheduler: BackgroundScheduler) -> dict:
    """Return a status dict for the /health endpoint."""
    paused = runtime_config.get_scheduler_paused()
    if paused:
        scheduler_state = "paused"
    elif scheduler.running:
        scheduler_state = "running"
    else:
        scheduler_state = "stopped"
    return {
        "status": "ok" if scheduler.running else "degraded",
        "scheduler": scheduler_state,
        "last_run_at": runtime_config.get_last_run_at(),
        "next_run_at": runtime_config.get_next_run_at(),
        "is_running": runtime_config.is_running(),
        "scans_paused": paused,
    }


def _validate_loki_endpoint(loki_url: str) -> None:
    """Validate that Loki endpoint is reachable."""
    try:
        response = requests.head(loki_url, timeout=5)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning(
            "Environment: Loki endpoint '%s' timed out after 5s. "
            "Check if Loki is slow, overloaded, or unreachable.",
            loki_url,
        )
    except requests.exceptions.ConnectionError as e:
        logger.warning(
            "Environment: Loki endpoint '%s' is unreachable: %s. "
            "Check network connectivity, DNS resolution, and URL correctness.",
            loki_url,
            e,
        )
    except requests.exceptions.HTTPError as e:
        logger.warning(
            "Environment: Loki endpoint '%s' returned HTTP error: %s. "
            "Check authentication, permissions, and endpoint configuration.",
            loki_url,
            e,
        )
    except requests.exceptions.RequestException as e:
        logger.warning(
            "Environment: Loki endpoint '%s' validation failed: %s.",
            loki_url,
            e,
        )


def _validate_environment() -> None:
    """Warn about misconfigured or unreachable services at startup."""
    enabled = runtime_config.get_enabled_exporters(default=config.ENABLED_EXPORTERS)
    if "loki" in enabled:
        loki_url = config.LOKI_URL
        if not loki_url:
            logger.warning(
                "Environment: Loki exporter is enabled but LOKI_URL is not set."
            )
        else:
            _validate_loki_endpoint(loki_url)


def main():
    """Entry point — initialises the scheduler and runs the polling loop."""
    logger.info("Hermes starting...")
    logger.info(
        "Config — interval: %smin | run on startup: %s | log level: %s",
        config.SPEEDTEST_INTERVAL_MINUTES,
        config.RUN_ON_STARTUP,
        config.LOG_LEVEL,
    )

    # Clean up any stale running sentinel left by a previous crash/restart.
    runtime_config.mark_done()

    _validate_environment()

    service = SpeedtestRunner()
    dispatcher = build_dispatcher()
    alert_manager = build_alert_manager()

    # Make alert_manager accessible to API routes
    shared_state.set_alert_manager(alert_manager)

    # Run immediately on startup if configured
    if config.RUN_ON_STARTUP:
        logger.info("RUN_ON_STARTUP is set — running initial test...")
        run_once(service, dispatcher, alert_manager)

    # Start the background scheduler
    scheduler = build_scheduler(service, dispatcher, alert_manager)
    scheduler.start()

    # Start the health endpoint
    health = HealthServer(
        port=config.HEALTH_PORT,
        get_status=lambda: _build_health_status(scheduler),
    )
    health.start()

    logger.info(
        "Scheduler started — next run in %s minutes.",
        config.SPEEDTEST_INTERVAL_MINUTES,
    )

    # Persist initial next run time immediately so the UI countdown is populated.
    _initial_job = scheduler.get_job("speedtest_run")
    if _initial_job and _initial_job.next_run_time:
        runtime_config.set_next_run_at(_initial_job.next_run_time.isoformat())

    last_interval = runtime_config.get_interval_minutes(
        default=config.SPEEDTEST_INTERVAL_MINUTES
    )
    last_exporters = runtime_config.get_enabled_exporters(
        default=config.ENABLED_EXPORTERS
    )
    last_alert_config = runtime_config.get_alert_config()
    last_next_run_time = None

    # Restore paused state persisted from before a restart.
    last_paused = runtime_config.get_scheduler_paused()
    if last_paused:
        scheduler.pause_job("speedtest_run")
        logger.info("Automated scans are paused (restored from runtime config).")

    # Keep the main thread alive — scheduler runs in background thread.
    # Each cycle delegates to _poll_once for UI-driven change detection.
    try:
        while True:
            time.sleep(30)
            (
                last_interval,
                last_exporters,
                last_paused,
                last_alert_config,
                last_next_run_time,
            ) = _poll_once(
                scheduler,
                dispatcher,
                service,
                alert_manager,
                last_interval,
                last_exporters,
                last_paused,
                last_alert_config,
                last_next_run_time,
            )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received — stopping scheduler...")
        scheduler.shutdown()
        logger.info("Hermes stopped cleanly.")
        raise


if __name__ == "__main__":  # pragma: no cover
    main()
