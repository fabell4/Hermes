# main.py
"""
Hermes — entry point.
Wires all components together, starts the scheduler, and runs the application.
"""
import logging
import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from . import config
from . import runtime_config
from .runtime_config import set_interval_minutes, set_enabled_exporters
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
    "csv": lambda: CSVExporter(path=config.CSV_LOG_PATH),
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
            except Exception as e:
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
            except Exception as e:
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
    except DispatchError as e:
        logger.warning("Dispatch completed with failures:")
        for name, error in e.failures.items():
            logger.warning("  [%s] %s", name, error)


def build_scheduler(service: SpeedtestRunner, dispatcher: ResultDispatcher) -> BackgroundScheduler:
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
        max_instances=1,        # Prevent overlapping runs if a test takes longer than the interval
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


def main():
    logger.info("Hermes starting...")
    logger.info(
        "Config — interval: %smin | run on startup: %s | log level: %s",
        config.SPEEDTEST_INTERVAL_MINUTES,
        config.RUN_ON_STARTUP,
        config.LOG_LEVEL,
    )
    service = SpeedtestRunner()
    dispatcher = build_dispatcher()

    # Run immediately on startup if configured
    if config.RUN_ON_STARTUP:
        logger.info("RUN_ON_STARTUP is set — running initial test...")
        run_once(service, dispatcher)

    # Start the background scheduler
    scheduler = build_scheduler(service, dispatcher)
    scheduler.start()
    logger.info(
        "Scheduler started — next run in %s minutes.",
        config.SPEEDTEST_INTERVAL_MINUTES,
    )

    # Keep the main thread alive — scheduler runs in background thread
    try:
        while True:
            time.sleep(30)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received — stopping scheduler...")
        scheduler.shutdown()
        logger.info("Hermes stopped cleanly.")
        raise


if __name__ == "__main__":
    main()