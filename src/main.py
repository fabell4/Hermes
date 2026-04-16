# main.py
"""
Hermes — entry point.
Wires all components together, starts the scheduler, and runs the application.
"""

import logging
import sys
import time
import urllib.error
import urllib.request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from . import config
from . import runtime_config
from .runtime_config import set_interval_minutes, set_enabled_exporters
from .services.health_server import HealthServer
from .services.speedtest_runner import SpeedtestRunner
from .result_dispatcher import ResultDispatcher, DispatchError
from .exporters.csv_exporter import CSVExporter
from .exporters.prometheus_exporter import PrometheusExporter
from .exporters.loki_exporter import LokiExporter

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
# Uncomment each entry as the exporter is implemented.
EXPORTER_REGISTRY = {
    "csv": lambda: CSVExporter(
        path=config.CSV_LOG_PATH,
        max_rows=config.CSV_MAX_ROWS,
        retention_days=config.CSV_RETENTION_DAYS,
    ),
    "prometheus": lambda: PrometheusExporter(port=config.PROMETHEUS_PORT),
    "loki": _build_loki_exporter,
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
            except Exception as e:  # pylint: disable=broad-except
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
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Exporter '%s' could not be initialized: %s", name, e)
        else:
            logger.warning("Unknown exporter '%s' in enabled list — skipping.", name)

    set_enabled_exporters(enabled)
    logger.info("Exporters updated — active: %s", dispatcher.exporter_names)


def run_once(service: SpeedtestRunner, dispatcher: ResultDispatcher) -> None:
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
        except RuntimeError as e:
            logger.error("Speedtest failed: %s", e)
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
    service: SpeedtestRunner, dispatcher: ResultDispatcher
) -> BackgroundScheduler:
    """
    Configures and returns the background scheduler.
    Does not start it — caller decides when to start.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: run_once(service, dispatcher),
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
    last_interval: int,
    last_exporters: list[str],
    last_paused: bool = False,
) -> tuple[int, list[str], bool]:
    """
    Execute one poll cycle — checks runtime_config.json for UI-driven changes
    and reacts accordingly. Returns the (possibly updated) interval, exporters,
    and paused state.
    Extracted from the main loop to make it unit-testable.
    """
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

    # --- React to "Run Now" trigger written by the UI ---
    if runtime_config.consume_run_trigger():
        logger.info("Run trigger detected — starting immediate test.")
        run_once(service, dispatcher)

    # --- React to pause/resume toggle written by the UI ---
    current_paused = runtime_config.get_scheduler_paused()
    if current_paused != last_paused:
        job = scheduler.get_job("speedtest_run")
        if job:
            if current_paused:
                scheduler.pause_job("speedtest_run")
                logger.info("Automated scans paused.")
            else:
                scheduler.resume_job("speedtest_run")
                logger.info("Automated scans resumed.")
        last_paused = current_paused

    # --- Persist next run time for the UI countdown ---
    job = scheduler.get_job("speedtest_run")
    if job and job.next_run_time:
        runtime_config.set_next_run_at(job.next_run_time.isoformat())

    return last_interval, last_exporters, last_paused


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
            try:
                req = urllib.request.Request(loki_url, method="HEAD")
                urllib.request.urlopen(req, timeout=5)  # noqa: S310
            except urllib.error.URLError as e:
                logger.warning(
                    "Environment: Loki URL '%s' is unreachable — %s. "
                    "Loki exports will fail until the server is available.",
                    loki_url,
                    e.reason,
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(
                    "Environment: Could not verify Loki URL '%s' — %s.",
                    loki_url,
                    e,
                )


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

    # Run immediately on startup if configured
    if config.RUN_ON_STARTUP:
        logger.info("RUN_ON_STARTUP is set — running initial test...")
        run_once(service, dispatcher)

    # Start the background scheduler
    scheduler = build_scheduler(service, dispatcher)
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
            last_interval, last_exporters, last_paused = _poll_once(
                scheduler,
                dispatcher,
                service,
                last_interval,
                last_exporters,
                last_paused,
            )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received — stopping scheduler...")
        scheduler.shutdown()
        logger.info("Hermes stopped cleanly.")
        raise


if __name__ == "__main__":  # pragma: no cover
    main()
