"""CSVExporter — appends SpeedResult data to a CSV file and provides it for download."""

import csv
import logging
from pathlib import Path
from src.exporters.base_exporter import BaseExporter
from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)

# Defines column order in the CSV — must match the fields pulled from SpeedResult
FIELDNAMES = [
    "timestamp",
    "download_mbps",
    "upload_mbps",
    "ping_ms",
    "server_name",
    "server_location",
    "server_id",
]


class CSVExporter(BaseExporter):
    """
    Exports SpeedResult data to a CSV file.

    - Creates the file and writes headers if it doesn't exist
    - Appends one row per result
    - Provides file path for the web layer to serve as a download
    - Thread-safe for single-writer use (one scheduled runner at a time)
    """

    def __init__(self, path: str | Path = "logs/results.csv"):
        """
        Args:
            path: Where to write the CSV file.
                  Parent directories are created automatically.
        """
        self.path = Path(path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """
        Creates the CSV file with headers if it doesn't already exist.
        Also creates any missing parent directories.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            with open(self.path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
            logger.info("Created new CSV log file at: %s", self.path)

    def export(self, result: SpeedResult) -> None:
        """
        Appends a single row to the CSV file for this result.
        Called by the dispatcher on every completed speedtest run.
        """
        row = result.to_dict()

        # Ensure only the columns we care about are written, in the right order
        # This guards against to_dict() adding extra fields in the future
        filtered_row = {key: row[key] for key in FIELDNAMES}

        try:
            with open(self.path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writerow(filtered_row)
            logger.info(
                "CSV row written — down: %sMbps up: %sMbps ping: %sms",
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
            )
        except OSError as e:
            logger.error("Failed to write CSV row: %s", e)
            raise

    def get_file_path(self) -> Path:
        """
        Returns the absolute path to the CSV file.
        Used by the web layer to serve the file as a download.
        """
        return self.path.resolve()

    def get_row_count(self) -> int:
        """
        Returns the number of data rows in the CSV (excluding the header).
        Useful for the web UI to show how many runs have been logged.
        """
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as f:
            # subtract 1 for the header row
            return sum(1 for _ in f) - 1
