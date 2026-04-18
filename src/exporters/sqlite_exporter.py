"""SQLiteExporter — stores SpeedResult data in a SQLite database."""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

from src.exporters.base_exporter import BaseExporter
from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    download_mbps   REAL    NOT NULL,
    upload_mbps     REAL    NOT NULL,
    ping_ms         REAL    NOT NULL,
    jitter_ms       REAL,
    isp_name        TEXT,
    server_name     TEXT    NOT NULL,
    server_location TEXT    NOT NULL,
    server_id       INTEGER
)"""

_INSERT = """
INSERT INTO results
    (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
     server_name, server_location, server_id)
VALUES
    (:timestamp, :download_mbps, :upload_mbps, :ping_ms, :jitter_ms, :isp_name,
     :server_name, :server_location, :server_id)"""


class SQLiteExporter(BaseExporter):
    """
    Exports SpeedResult data to a SQLite database.

    - Creates the database and table on first use.
    - Appends one row per result.
    - Optionally prunes rows older than retention_days or exceeding max_rows.
    - Thread-safe via an internal write lock; uses WAL journal mode for
      concurrent read access from the Streamlit UI process.
    """

    def __init__(
        self,
        path: str | Path = "data/hermes.db",
        max_rows: int = 0,
        retention_days: int = 0,
    ) -> None:
        """
        Args:
            path: Where to write the SQLite database file.
                  Parent directories are created automatically.
            max_rows: Maximum number of rows to keep. 0 means unlimited.
            retention_days: Delete rows older than this many days. 0 means unlimited.
        """
        self.path = Path(path)
        self.max_rows = max_rows
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a connection, yield it, commit on success, rollback + close on error."""
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Columns added after initial release; migrated automatically on startup.
    _MIGRATIONS: list[tuple[str, str]] = [
        ("jitter_ms", "ALTER TABLE results ADD COLUMN jitter_ms REAL"),
        ("isp_name", "ALTER TABLE results ADD COLUMN isp_name TEXT"),
    ]

    def _init_db(self) -> None:
        """Creates the database file and results table if they do not exist.

        Also runs lightweight column-addition migrations so that databases
        created by older versions of Hermes gain new columns automatically.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._transaction() as conn:
            conn.execute(_CREATE_TABLE)
            existing = {
                row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()
            }
            for column, ddl in self._MIGRATIONS:
                if column not in existing:
                    conn.execute(ddl)
                    logger.info("Migrated SQLite schema: added column '%s'", column)
        logger.info("SQLite database ready at: %s", self.path)

    def export(self, result: SpeedResult) -> None:
        """Appends a single row to the database, then prunes if limits are set."""
        row = {
            "timestamp": result.timestamp.isoformat(),
            "download_mbps": result.download_mbps,
            "upload_mbps": result.upload_mbps,
            "ping_ms": result.ping_ms,
            "jitter_ms": result.jitter_ms,
            "isp_name": result.isp_name,
            "server_name": result.server_name,
            "server_location": result.server_location,
            "server_id": result.server_id,
        }
        with self._lock:
            try:
                with self._transaction() as conn:
                    conn.execute(_INSERT, row)
                    self._prune(conn)
            except sqlite3.Error as e:
                logger.error("Failed to write SQLite row: %s", e)
                raise RuntimeError(f"SQLite write failed: {e}") from e
        logger.info(
            "SQLite row written — down: %sMbps up: %sMbps ping: %sms",
            result.download_mbps,
            result.upload_mbps,
            result.ping_ms,
        )

    def _prune(self, conn: sqlite3.Connection) -> None:
        """Removes rows exceeding max_rows or older than retention_days."""
        if not self.max_rows and not self.retention_days:
            return
        if self.retention_days:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            ).isoformat()
            conn.execute("DELETE FROM results WHERE timestamp < ?", (cutoff,))
        if self.max_rows:
            conn.execute(
                """
                DELETE FROM results WHERE id NOT IN (
                    SELECT id FROM results ORDER BY timestamp DESC LIMIT ?
                )
                """,
                (self.max_rows,),
            )
