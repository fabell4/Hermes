"""SQLiteExporter — stores SpeedResult data in a SQLite database."""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import ClassVar, Generator

from src.exporters.base_exporter import BaseExporter
from src.models.outage_event import OutageEvent
from src.models.speed_result import SpeedResult

logger = logging.getLogger(__name__)


class SQLiteLockTimeout(Exception):
    """Raised when SQLite lock cannot be acquired within timeout."""

    def __init__(self, timeout: float, db_path: str | Path):
        self.timeout = timeout
        self.db_path = str(db_path)
        super().__init__(
            f"Could not acquire SQLite lock for {self.db_path} within {timeout}s. "
            f"Another process may be holding the lock or database may be busy. "
            f"Check for long-running queries or concurrent write operations."
        )


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
    server_id       INTEGER,
    packet_loss_pct REAL,
    quality_score   REAL,
    sla_ok          INTEGER
)"""

_CREATE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_results_timestamp ON results(timestamp DESC)"
)

_CREATE_OUTAGE_TABLE = """
CREATE TABLE IF NOT EXISTS outage_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type              TEXT    NOT NULL,
    timestamp               TEXT    NOT NULL,
    duration_seconds        REAL,
    isp_name                TEXT,
    asn                     TEXT,
    bgp_unstable            INTEGER,
    cloudflare_outage_desc  TEXT,
    probe_results           TEXT    NOT NULL
)"""

_CREATE_OUTAGE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_outage_events_timestamp "
    "ON outage_events(timestamp DESC)"
)

_INSERT_OUTAGE = """
INSERT INTO outage_events
    (event_type, timestamp, duration_seconds, isp_name, asn,
     bgp_unstable, cloudflare_outage_desc, probe_results)
VALUES
    (:event_type, :timestamp, :duration_seconds, :isp_name, :asn,
     :bgp_unstable, :cloudflare_outage_desc, :probe_results)"""

_INSERT = """
INSERT INTO results
    (timestamp, download_mbps, upload_mbps, ping_ms, jitter_ms, isp_name,
     server_name, server_location, server_id, packet_loss_pct, quality_score, sla_ok)
VALUES
    (:timestamp, :download_mbps, :upload_mbps, :ping_ms, :jitter_ms, :isp_name,
     :server_name, :server_location, :server_id, :packet_loss_pct, :quality_score, :sla_ok)"""


class SQLiteExporter(BaseExporter):
    """
    Exports SpeedResult data to a SQLite database.

    - Creates the database and table on first use.
    - Appends one row per result.
    - Optionally prunes rows older than retention_days or exceeding max_rows.
    - Thread-safe via an internal write lock; uses WAL journal mode for
      concurrent read access from the Streamlit UI process.
    """

    # Serialises concurrent _init_db() calls to the same database path across
    # different SQLiteExporter instances (e.g., multiple threads each creating
    # their own instance against the same file).
    _path_locks: ClassVar[dict[str, threading.Lock]] = {}
    _path_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _get_path_lock(cls, path: Path) -> threading.Lock:
        key = str(path.resolve())
        with cls._path_locks_guard:
            if key not in cls._path_locks:
                cls._path_locks[key] = threading.Lock()
            return cls._path_locks[key]

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
        conn = sqlite3.connect(str(self.path), timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Columns and indexes added after initial release; migrated automatically on startup.
    _MIGRATIONS: list[tuple[str, str]] = [
        ("jitter_ms", "ALTER TABLE results ADD COLUMN jitter_ms REAL"),
        ("isp_name", "ALTER TABLE results ADD COLUMN isp_name TEXT"),
        (
            "idx_results_timestamp",
            "CREATE INDEX IF NOT EXISTS idx_results_timestamp ON results(timestamp DESC)",
        ),
        ("packet_loss_pct", "ALTER TABLE results ADD COLUMN packet_loss_pct REAL"),
        ("quality_score", "ALTER TABLE results ADD COLUMN quality_score REAL"),
        ("sla_ok", "ALTER TABLE results ADD COLUMN sla_ok INTEGER"),
        ("note", "ALTER TABLE results ADD COLUMN note TEXT"),
        ("add_outage_events_table", _CREATE_OUTAGE_TABLE),
        ("idx_outage_events_timestamp", _CREATE_OUTAGE_INDEX),
    ]

    def _init_db(self) -> None:
        """Creates the database file and results table if they do not exist.

        Also runs lightweight schema migrations so that databases created by
        older versions of Hermes gain new columns and indexes automatically.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        path_lock = self._get_path_lock(self.path)
        with path_lock:
            with self._transaction() as conn:
                conn.execute(_CREATE_TABLE)
                conn.execute(_CREATE_INDEX)

                # Check for missing columns
                existing_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(results)").fetchall()
                }

                # Check for missing indexes
                existing_indexes = {
                    row[1]
                    for row in conn.execute("PRAGMA index_list(results)").fetchall()
                }

                for name, ddl in self._MIGRATIONS:
                    # Check if it's a column or index migration
                    if name.startswith("idx_"):
                        # Index migration
                        if name not in existing_indexes:
                            conn.execute(ddl)
                            logger.info(
                                "Migrated SQLite schema: added index '%s'", name
                            )
                    elif name.startswith("add_") and "table" in name:
                        # CREATE TABLE migration — safe to run every time (IF NOT EXISTS)
                        conn.execute(ddl)
                        logger.debug("Ensured table via migration '%s'", name)
                    else:
                        # Column migration
                        if name not in existing_columns:
                            conn.execute(ddl)
                            logger.info(
                                "Migrated SQLite schema: added column '%s'", name
                            )
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
            "packet_loss_pct": result.packet_loss_pct,
            "quality_score": result.quality_score,
            # SQLite has no bool type; store as 1/0/NULL
            "sla_ok": (None if result.sla_ok is None else int(result.sla_ok)),
        }

        # Try to acquire lock with timeout to prevent deadlock
        acquired = self._lock.acquire(timeout=30.0)
        if not acquired:
            raise SQLiteLockTimeout(timeout=30.0, db_path=self.path)

        pruned = False
        try:
            try:
                with self._transaction() as conn:
                    conn.execute(_INSERT, row)
                    pruned = self._prune(conn)
            except sqlite3.Error as e:
                logger.error("Failed to write SQLite row: %s", e)
                raise RuntimeError(f"SQLite write failed: {e}") from e
        finally:
            self._lock.release()

        if pruned:
            self._checkpoint_and_maybe_vacuum()

        logger.info(
            "SQLite row written — down: %sMbps up: %sMbps ping: %sms",
            result.download_mbps,
            result.upload_mbps,
            result.ping_ms,
        )

    def export_outage_event(self, event: OutageEvent) -> None:
        """Persist a single OutageEvent row to the outage_events table."""
        row = {
            "event_type": str(event.event_type),
            "timestamp": event.timestamp.isoformat(),
            "duration_seconds": event.duration_seconds,
            "isp_name": event.isp_name,
            "asn": event.asn,
            "bgp_unstable": (
                None if event.bgp_unstable is None else int(event.bgp_unstable)
            ),
            "cloudflare_outage_desc": event.cloudflare_outage_desc,
            "probe_results": event.probe_results,
        }
        acquired = self._lock.acquire(timeout=30.0)
        if not acquired:
            raise SQLiteLockTimeout(timeout=30.0, db_path=self.path)
        try:
            try:
                with self._transaction() as conn:
                    conn.execute(_INSERT_OUTAGE, row)
            except sqlite3.Error as e:
                logger.error("Failed to write outage_event row: %s", e)
                raise RuntimeError(f"SQLite write failed: {e}") from e
        finally:
            self._lock.release()
        logger.info(
            "Outage event recorded — type: %s timestamp: %s",
            event.event_type,
            event.timestamp.isoformat(),
        )

    def _prune(self, conn: sqlite3.Connection) -> bool:
        """Removes rows exceeding max_rows or older than retention_days.

        Returns:
            True if any rows were deleted, False otherwise.
        """
        if not self.max_rows and not self.retention_days:
            return False
        deleted = False
        if self.retention_days:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            ).isoformat()
            conn.execute("DELETE FROM results WHERE timestamp < ?", (cutoff,))
            deleted = deleted or conn.execute("SELECT changes()").fetchone()[0] > 0
        if self.max_rows:
            conn.execute(
                """
                DELETE FROM results WHERE id NOT IN (
                    SELECT id FROM results ORDER BY timestamp DESC LIMIT ?
                )
                """,
                (self.max_rows,),
            )
            deleted = deleted or conn.execute("SELECT changes()").fetchone()[0] > 0
        return deleted

    # ------------------------------------------------------------------
    # WAL checkpoint + vacuum helpers (called after prune)
    # ------------------------------------------------------------------

    #: Fragmentation ratio above which VACUUM is triggered (20 %).
    _VACUUM_THRESHOLD = 0.20

    def _checkpoint_and_maybe_vacuum(self) -> None:
        """Run a WAL checkpoint then VACUUM if fragmentation exceeds threshold.

        Executed outside the write transaction so that both operations can
        acquire the exclusive lock they need.  Failures are logged as warnings
        and never propagate — pruning already succeeded.
        """
        try:
            # isolation_level=None disables Python's implicit transaction wrapper
            # so that VACUUM (which cannot run inside a transaction) succeeds.
            conn = sqlite3.connect(
                self.path, isolation_level=None, check_same_thread=False
            )
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                logger.debug("WAL checkpoint completed for %s", self.path)

                row = conn.execute(
                    "SELECT freelist_count, page_count FROM pragma_freelist_count, pragma_page_count"
                ).fetchone()
                if row is None:
                    # Fallback: query pragmas individually
                    freelist = conn.execute("PRAGMA freelist_count").fetchone()[0]
                    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                else:
                    freelist, page_count = row

                if page_count > 0 and freelist / page_count > self._VACUUM_THRESHOLD:
                    logger.info(
                        "SQLite fragmentation %.0f%% exceeds threshold — running VACUUM on %s",
                        100.0 * freelist / page_count,
                        self.path,
                    )
                    conn.execute("VACUUM")
                    logger.info("VACUUM completed for %s", self.path)
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("SQLite checkpoint/vacuum failed (non-fatal): %s", exc)
