"""CSVExporter — appends SpeedResult data to a CSV file and provides it for download."""

import csv
import logging
from datetime import datetime, timezone, timedelta
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
    "jitter_ms",
    "isp_name",
    "server_name",
    "server_location",
    "server_id",
]


class CSVExporter(BaseExporter):
    """
    Exports SpeedResult data to a CSV file.

    - Creates the file and writes headers if it doesn't exist
    - Appends one row per result
    - Optionally prunes rows exceeding max_rows or older than retention_days
    - Provides file path for the web layer to serve as a download
    - Thread-safe for single-writer use (one scheduled runner at a time)
    """

    def __init__(
        self,
        path: str | Path = "logs/results.csv",
        max_rows: int = 0,
        retention_days: int = 0,
    ):
        """
        Args:
            path: Where to write the CSV file.
                  Parent directories are created automatically.
            max_rows: Maximum number of data rows to keep. 0 means unlimited.
            retention_days: Delete rows older than this many days. 0 means unlimited.
        """
        self.path = Path(path)
        self.max_rows = max_rows
        self.retention_days = retention_days
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
        Appends a single row to the CSV file for this result,
        then prunes stale rows if retention limits are configured.
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

        self._prune()

    def _filter_by_retention(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        """Filter rows older than retention_days."""
        if not self.retention_days:
            return rows

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.retention_days)
        return [
            r
            for r in rows
            if datetime.fromisoformat(r["timestamp"]).astimezone(timezone.utc) >= cutoff
        ]

    def _filter_by_max_rows(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        """Keep only the most recent max_rows."""
        if not self.max_rows or len(rows) <= self.max_rows:
            return rows
        return rows[-self.max_rows :]

    def _write_pruned_rows(self, rows: list[dict[str, str]]) -> None:
        """Write filtered rows to CSV file atomically."""
        temp_path = self.path.with_suffix(".tmp")
        try:
            with open(temp_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(rows)
            temp_path.replace(self.path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def _prune(self) -> None:
        """
        Removes rows that exceed max_rows or are older than retention_days.
        Rewrites the file in place if any rows are removed.
        Both limits are applied together — whichever removes more rows wins.
        """
        if not self.max_rows and not self.retention_days:
            return
        if not self.path.exists():
            return

        with open(self.path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        original_count = len(rows)
        rows = self._filter_by_retention(rows)
        rows = self._filter_by_max_rows(rows)

        removed = original_count - len(rows)
        if removed == 0:
            return

        self._write_pruned_rows(rows)
        logger.info("CSV pruned — removed %d row(s), %d remaining.", removed, len(rows))

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
