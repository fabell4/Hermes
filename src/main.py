# main.py

"""
Entry point — wires all components together and runs the application.
"""

import logging
import sys
from src.services.speedtest_runner import SpeedtestRunner
from src.result_dispatcher import ResultDispatcher, DispatchError
from src.exporters.csv_exporter import CSVExporter

# --- Logging setup ---
# Configure once here at the entry point — all modules use logging.getLogger(__name__)
# and will inherit this configuration automatically
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),          # Console output
        logging.FileHandler("logs/speedtest.log"),  # Persistent log file
    ],
)

logger = logging.getLogger(__name__)


def build_dispatcher() -> ResultDispatcher:
    """
    Instantiates and registers all exporters.
    Add new exporters here as they are built — nothing else needs to change.
    """
    dispatcher = ResultDispatcher()
    dispatcher.add_exporter("csv", CSVExporter(path="logs/results.csv"))
    # dispatcher.add_exporter("prometheus", PrometheusExporter(port=8000))  # coming soon
    # dispatcher.add_exporter("loki", LokiExporter(url="http://localhost:3100"))  # coming soon
    return dispatcher


def run_once(service: SpeedtestRunner, dispatcher: ResultDispatcher) -> None:
    """
    Runs a single speedtest and dispatches the result to all exporters.
    Separated from main() so the web layer can call this directly later.
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
        # Some exporters failed but others may have succeeded
        # Log each failure individually and continue — don't crash the app
        logger.warning("Dispatch completed with failures:")
        for name, error in e.failures.items():
            logger.warning("  [%s] %s", name, error)


def main():
    logger.info("Speedtest app starting...")

    service = SpeedtestRunner()
    dispatcher = build_dispatcher()

    run_once(service, dispatcher)

    logger.info("Done.")


if __name__ == "__main__":
    main()