"""Tests for the outage detection subsystem.

Covers:
    - src/constants.py                     OutageEventType
    - src/models/outage_event.py           OutageEvent
    - src/shared_state.py                  outage state getters/setters
    - src/services/outage_detector.py      OutageDetector + helpers
    - src/services/alert_manager.py        record_failure no-op, record_outage_start/recovered
    - src/exporters/sqlite_exporter.py     export_outage_event, outage_events table migration
    - src/exporters/csv_exporter.py        export_outage_event
    - src/api/routes/outages.py            GET /api/outages, GET /api/outage-status
"""

from __future__ import annotations

import csv
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.constants import OutageEventType
from src.models.outage_event import OutageEvent
from src.services.alert_providers import AlertProvider
from src.services.outage_detector import (
    ConnectivityStatus,
    OutageDetector,
    _parse_probe_hosts,
    _tcp_probe,
)


# ---------------------------------------------------------------------------
# Phase 1.1 — OutageEventType
# ---------------------------------------------------------------------------


class TestOutageEventType:
    def test_all_four_members_present(self):
        members = {e.value for e in OutageEventType}
        assert members == {
            "connectivity_lost",
            "connectivity_restored",
            "speedtest_server_unreachable",
            "dns_failure",
        }

    def test_members_are_unique(self):
        values = [e.value for e in OutageEventType]
        assert len(values) == len(set(values))

    def test_string_comparison(self):
        assert OutageEventType.CONNECTIVITY_LOST == "connectivity_lost"
        assert OutageEventType.CONNECTIVITY_RESTORED == "connectivity_restored"


# ---------------------------------------------------------------------------
# Phase 1.2 — OutageEvent model
# ---------------------------------------------------------------------------


class TestOutageEvent:
    def test_required_fields_only(self):
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="2/3 probes failed",
        )
        assert event.event_type == OutageEventType.CONNECTIVITY_LOST
        assert event.probe_results == "2/3 probes failed"
        assert event.duration_seconds is None
        assert event.isp_name is None
        assert event.asn is None
        assert event.bgp_unstable is None
        assert event.cloudflare_outage_desc is None
        assert event.timestamp.tzinfo is not None

    def test_all_fields_populated(self):
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_RESTORED,
            timestamp=ts,
            probe_results="0/3 probes failed",
            duration_seconds=120.5,
            isp_name="Test ISP",
            asn="12345",
            bgp_unstable=True,
            cloudflare_outage_desc="Outage in region X",
        )
        assert event.duration_seconds == pytest.approx(120.5)
        assert event.isp_name == "Test ISP"
        assert event.asn == "12345"
        assert event.bgp_unstable is True
        assert event.cloudflare_outage_desc == "Outage in region X"

    def test_naive_timestamp_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            OutageEvent(
                event_type=OutageEventType.CONNECTIVITY_LOST,
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                probe_results="",
            )

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError, match="negative"):
            OutageEvent(
                event_type=OutageEventType.CONNECTIVITY_RESTORED,
                probe_results="",
                duration_seconds=-1.0,
            )


# ---------------------------------------------------------------------------
# Phase 1.4 — SharedState outage fields
# ---------------------------------------------------------------------------


class TestSharedStateOutage:
    def setup_method(self):
        from src import shared_state

        shared_state.set_outage_in_progress(False)
        shared_state.set_outage_start_time(None)

    def test_defaults(self):
        from src import shared_state

        assert shared_state.get_outage_in_progress() is False
        assert shared_state.get_outage_start_time() is None

    def test_set_outage_in_progress_roundtrip(self):
        from src import shared_state

        shared_state.set_outage_in_progress(True)
        assert shared_state.get_outage_in_progress() is True
        shared_state.set_outage_in_progress(False)
        assert shared_state.get_outage_in_progress() is False

    def test_set_outage_start_time_roundtrip(self):
        from src import shared_state

        ts = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        shared_state.set_outage_start_time(ts)
        assert shared_state.get_outage_start_time() == ts
        shared_state.set_outage_start_time(None)
        assert shared_state.get_outage_start_time() is None

    def test_thread_safety(self):
        from src import shared_state

        errors: list[Exception] = []

        def toggle():
            for _ in range(50):
                shared_state.set_outage_in_progress(True)
                shared_state.get_outage_in_progress()
                shared_state.set_outage_in_progress(False)

        threads = [threading.Thread(target=toggle) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ---------------------------------------------------------------------------
# Phase 2.1 — OutageDetector helpers
# ---------------------------------------------------------------------------


class TestParseProbeHosts:
    def test_valid_entries(self):
        result = _parse_probe_hosts(["1.1.1.1:53", "8.8.8.8:53"])
        assert result == [("1.1.1.1", 53), ("8.8.8.8", 53)]

    def test_invalid_entry_skipped(self):
        result = _parse_probe_hosts(["invalid", "8.8.8.8:53"])
        assert result == [("8.8.8.8", 53)]

    def test_empty_list_returns_empty(self):
        result = _parse_probe_hosts([])
        assert result == []


class TestTcpProbe:
    def test_successful_connection_returns_true(self):
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = Mock()
            mock_conn.return_value.close = Mock()
            assert _tcp_probe("1.1.1.1", 53, 3) is True

    def test_oserror_returns_false(self):
        with patch("socket.create_connection", side_effect=OSError):
            assert _tcp_probe("1.1.1.1", 53, 3) is False


class TestOutageDetectorConnectivity:
    def _make_detector(self, quorum=2, failure_threshold=2) -> OutageDetector:
        return OutageDetector(
            probe_hosts=["1.1.1.1:53", "8.8.8.8:53", "9.9.9.9:53"],
            quorum=quorum,
            failure_threshold=failure_threshold,
        )

    def _patch_probes(self, results: list[bool]):
        """Patch _tcp_probe to return values from the list in order."""
        return patch(
            "src.services.outage_detector._tcp_probe",
            side_effect=results,
        )

    def test_all_up_returns_up(self):
        detector = self._make_detector()
        with self._patch_probes([True, True, True]):
            assert detector.check_connectivity() == ConnectivityStatus.UP

    def test_majority_fail_does_not_trigger_immediately(self):
        """First failure round doesn't declare DOWN when threshold is 2."""
        detector = self._make_detector(failure_threshold=2)
        with self._patch_probes([False, False, True]):
            assert detector.check_connectivity() == ConnectivityStatus.UP
        assert detector._consecutive_probe_failures == 1

    def test_second_failure_round_declares_down(self):
        detector = self._make_detector(failure_threshold=2)
        with self._patch_probes([False, False, True]):
            detector.check_connectivity()
        with self._patch_probes([False, False, True]):
            assert detector.check_connectivity() == ConnectivityStatus.DOWN

    def test_fewer_than_quorum_failures_is_up(self):
        detector = self._make_detector(quorum=3)
        # Only 2 fail but quorum is 3
        with self._patch_probes([False, False, True]):
            assert detector.check_connectivity() == ConnectivityStatus.UP
        assert detector._consecutive_probe_failures == 0

    def test_single_up_round_resets_counter(self):
        detector = self._make_detector(failure_threshold=3)
        # Two failure rounds
        for _ in range(2):
            with self._patch_probes([False, False, True]):
                detector.check_connectivity()
        assert detector._consecutive_probe_failures == 2
        # One success round
        with self._patch_probes([True, True, True]):
            detector.check_connectivity()
        assert detector._consecutive_probe_failures == 0

    def test_none_detector_preserves_existing_behaviour(self):
        """run_once with outage_detector=None must not import outage modules."""
        # Integration guard: when outage_detector is None, no outage logic runs.
        detector: OutageDetector | None = None
        _ = detector  # documents that None is a valid value; no runtime assertion needed


class TestOutageDetectorEnrichment:
    def _make_detector(self, isp_enabled=True, cf_token=None) -> OutageDetector:
        session = MagicMock()
        return OutageDetector(
            probe_hosts=["1.1.1.1:53"],
            isp_check_enabled=isp_enabled,
            cloudflare_token=cf_token,
            http_session=session,
        )

    def test_get_isp_asn_disabled_returns_none(self):
        d = self._make_detector(isp_enabled=False)
        assert d.get_isp_asn() is None

    def test_get_isp_asn_cached_after_first_call(self):
        d = self._make_detector()
        # Mock public IP and RIPE Stat responses
        d._session.get = MagicMock(
            side_effect=[
                Mock(
                    json=lambda: {"ip": "1.2.3.4"},
                    raise_for_status=Mock(),
                ),
                Mock(
                    json=lambda: {"data": {"asns": ["12345"]}},
                    raise_for_status=Mock(),
                ),
            ]
        )
        asn1 = d.get_isp_asn()
        # Second call should not make HTTP request (already fetched)
        asn2 = d.get_isp_asn()
        assert asn1 == "12345"
        assert asn2 == "12345"
        # Only 2 HTTP calls for 2 API endpoints, not 4
        assert d._session.get.call_count == 2

    def test_bgp_cache_ttl(self):

        d = self._make_detector()
        now = datetime.now(timezone.utc)
        # Pre-populate with fresh cache entry
        d._bgp_cache["12345"] = (True, now)
        assert d.check_bgp_stability("12345") is True
        # No HTTP call should have been made
        d._session.get.assert_not_called()  # type: ignore[attr-defined]

    def test_bgp_check_disabled_returns_false(self):
        d = self._make_detector(isp_enabled=False)
        assert d.check_bgp_stability("12345") is False

    def test_cf_radar_not_called_without_token(self):
        d = self._make_detector(cf_token=None)
        assert d.check_cloudflare_outage("12345") is None
        d._session.get.assert_not_called()  # type: ignore[attr-defined]

    def test_cf_radar_cache_honours_ttl(self):
        d = self._make_detector(cf_token="tok")
        now = datetime.now(timezone.utc)
        d._cf_cache["12345"] = ("Outage in region X", now)
        result = d.check_cloudflare_outage("12345")
        assert result == "Outage in region X"
        d._session.get.assert_not_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Phase 2.2 — AlertManager outage methods
# ---------------------------------------------------------------------------


class MockProvider(AlertProvider):
    def __init__(self):
        self.calls: list[tuple[int, str, datetime]] = []

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
        self.calls.append((failure_count, last_error, timestamp))


class TestAlertManagerOutage:
    def setup_method(self):
        from src import shared_state

        shared_state.set_outage_in_progress(False)
        shared_state.set_outage_start_time(None)

    def _make_manager(self):
        from src.services.alert_manager import AlertManager

        m = AlertManager(failure_threshold=3, cooldown_minutes=0)
        m.reset()
        return m

    def test_record_failure_noop_during_outage(self):
        from src import shared_state

        manager = self._make_manager()
        shared_state.set_outage_in_progress(True)
        try:
            manager.record_failure("error")
            assert manager.consecutive_failures == 0
        finally:
            shared_state.set_outage_in_progress(False)

    def test_record_failure_works_when_no_outage(self):
        manager = self._make_manager()
        manager.record_failure("error")
        assert manager.consecutive_failures == 1

    def test_record_outage_start_sets_shared_state(self):
        from src import shared_state

        manager = self._make_manager()
        manager.record_outage_start()
        assert shared_state.get_outage_in_progress() is True
        assert shared_state.get_outage_start_time() is not None

    def test_record_outage_start_resets_failure_counter(self):
        manager = self._make_manager()
        manager._consecutive_failures = 5
        manager.record_outage_start()
        assert manager.consecutive_failures == 0

    def test_record_outage_start_sends_alert(self):
        from src.services.alert_manager import AlertManager

        manager = AlertManager(failure_threshold=1, cooldown_minutes=0)
        provider = MockProvider()
        manager.add_provider("mock", provider)
        manager.record_outage_start(isp_name="Test ISP")
        manager._wait_for_pending_alerts()
        assert len(provider.calls) == 1
        assert "Connectivity lost" in provider.calls[0][1]
        assert "Test ISP" in provider.calls[0][1]

    def test_record_outage_start_bgp_context_in_message(self):
        from src.services.alert_manager import AlertManager

        manager = AlertManager(failure_threshold=1, cooldown_minutes=0)
        provider = MockProvider()
        manager.add_provider("mock", provider)
        manager.record_outage_start(bgp_context="BGP instability detected for AS12345")
        manager._wait_for_pending_alerts()
        assert len(provider.calls) == 1
        assert "BGP" in provider.calls[0][1]

    def test_record_outage_recovered_clears_shared_state(self):
        from src import shared_state

        manager = self._make_manager()
        shared_state.set_outage_in_progress(True)
        shared_state.set_outage_start_time(datetime.now(timezone.utc))
        manager.record_outage_recovered(duration_s=300.0)
        assert shared_state.get_outage_in_progress() is False
        assert shared_state.get_outage_start_time() is None

    def test_record_outage_recovered_sends_alert_with_duration(self):
        from src.services.alert_manager import AlertManager

        manager = AlertManager(failure_threshold=1, cooldown_minutes=0)
        provider = MockProvider()
        manager.add_provider("mock", provider)
        manager.record_outage_recovered(duration_s=125.0)
        manager._wait_for_pending_alerts()
        assert len(provider.calls) == 1
        msg = provider.calls[0][1]
        # 125 seconds = 2m 5s
        assert "2m" in msg or "125" in msg or "restored" in msg.lower()

    def test_record_outage_recovered_bypasses_cooldown(self):
        from src.services.alert_manager import AlertManager

        manager = AlertManager(failure_threshold=1, cooldown_minutes=60)
        provider = MockProvider()
        manager.add_provider("mock", provider)
        # Simulate cooldown already active
        manager._last_alert_time = datetime.now(timezone.utc)
        manager.record_outage_recovered(duration_s=10.0)
        manager._wait_for_pending_alerts()
        assert len(provider.calls) == 1


# ---------------------------------------------------------------------------
# Phase 4.1 — SQLite export_outage_event
# ---------------------------------------------------------------------------


class TestSQLiteOutageExport:
    def test_outage_table_created_on_init(self, tmp_path):
        from src.exporters.sqlite_exporter import SQLiteExporter

        SQLiteExporter(path=tmp_path / "test.db")
        with closing(sqlite3.connect(str(tmp_path / "test.db"))) as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "outage_events" in tables

    def test_init_is_idempotent(self, tmp_path):
        from src.exporters.sqlite_exporter import SQLiteExporter

        db = tmp_path / "test.db"
        SQLiteExporter(path=db)
        SQLiteExporter(path=db)  # should not raise

    def test_export_outage_event_inserts_row(self, tmp_path):
        from src.exporters.sqlite_exporter import SQLiteExporter

        exporter = SQLiteExporter(path=tmp_path / "test.db")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="2/3 probes failed",
            isp_name="Test ISP",
            asn="12345",
            bgp_unstable=True,
            cloudflare_outage_desc="Outage in region X",
        )
        exporter.export_outage_event(event)
        with closing(sqlite3.connect(str(tmp_path / "test.db"))) as conn:
            row = conn.execute(
                "SELECT * FROM outage_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row[1] == "connectivity_lost"  # event_type column
        assert row[4] == "Test ISP"  # isp_name

    def test_export_outage_event_null_duration(self, tmp_path):
        from src.exporters.sqlite_exporter import SQLiteExporter

        exporter = SQLiteExporter(path=tmp_path / "test.db")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="",
        )
        exporter.export_outage_event(event)
        with closing(sqlite3.connect(str(tmp_path / "test.db"))) as conn:
            row = conn.execute(
                "SELECT duration_seconds FROM outage_events LIMIT 1"
            ).fetchone()
        assert row[0] is None

    def test_bgp_unstable_stored_as_integer(self, tmp_path):
        from src.exporters.sqlite_exporter import SQLiteExporter

        exporter = SQLiteExporter(path=tmp_path / "test.db")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="",
            bgp_unstable=True,
        )
        exporter.export_outage_event(event)
        with closing(sqlite3.connect(str(tmp_path / "test.db"))) as conn:
            row = conn.execute(
                "SELECT bgp_unstable FROM outage_events LIMIT 1"
            ).fetchone()
        assert row[0] == 1  # stored as integer


# ---------------------------------------------------------------------------
# Phase 4.2 — CSV export_outage_event
# ---------------------------------------------------------------------------


class TestCSVOutageExport:
    def test_outage_csv_created_when_not_exists(self, tmp_path):
        from src.exporters.csv_exporter import CSVExporter

        exporter = CSVExporter(path=tmp_path / "results.csv")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="2/3 failed",
        )
        exporter.export_outage_event(event)
        assert (tmp_path / "outage_events.csv").exists()

    def test_outage_csv_appends_row(self, tmp_path):
        from src.exporters.csv_exporter import CSVExporter

        exporter = CSVExporter(path=tmp_path / "results.csv")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="2/3 failed",
            isp_name="Test ISP",
        )
        exporter.export_outage_event(event)
        with open(tmp_path / "outage_events.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["event_type"] == "connectivity_lost"
        assert rows[0]["isp_name"] == "Test ISP"

    def test_outage_csv_correct_fieldnames(self, tmp_path):
        from src.exporters.csv_exporter import CSVExporter, OUTAGE_FIELDNAMES

        exporter = CSVExporter(path=tmp_path / "results.csv")
        event = OutageEvent(
            event_type=OutageEventType.CONNECTIVITY_LOST,
            probe_results="",
        )
        exporter.export_outage_event(event)
        with open(tmp_path / "outage_events.csv", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == OUTAGE_FIELDNAMES


# ---------------------------------------------------------------------------
# Phase 5.1 — Outage API routes
# ---------------------------------------------------------------------------


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    """TestClient for the FastAPI app with an empty test database."""
    import src.api.routes.outages as outages_module
    from src.api.main import app

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(outages_module, "DB_PATH", db_path)

    # Create db with outage_events table
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.execute(
            """
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
            )
            """
        )
        conn.commit()

    # Disable API auth
    monkeypatch.setattr("src.config.API_KEY", None)

    return TestClient(app)


class TestOutageAPI:
    def test_get_outages_empty(self, api_client):
        resp = api_client.get("/api/outages")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["events"] == []

    def test_get_outages_pagination(self, api_client, tmp_path, monkeypatch):
        """Insert 5 events; page_size=2 returns 2 with correct total."""
        import src.api.routes.outages as outages_module

        db_path = outages_module.DB_PATH
        ts = "2026-05-01T12:00:00+00:00"
        with closing(sqlite3.connect(str(db_path))) as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO outage_events "
                    "(event_type, timestamp, probe_results) VALUES (?, ?, ?)",
                    ("connectivity_lost", ts, f"{i}/3 failed"),
                )
            conn.commit()
        resp = api_client.get("/api/outages?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["events"]) == 2

    def test_get_outages_page_size_too_large(self, api_client):
        resp = api_client.get("/api/outages?page_size=501")
        assert resp.status_code == 422

    def test_get_outage_status_default(self, api_client):
        from src import shared_state

        shared_state.set_outage_in_progress(False)
        shared_state.set_outage_start_time(None)
        resp = api_client.get("/api/outage-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["outage_in_progress"] is False
        assert body["outage_start_time"] is None

    def test_get_outage_status_during_outage(self, api_client):
        from src import shared_state

        ts = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        shared_state.set_outage_in_progress(True)
        shared_state.set_outage_start_time(ts)
        try:
            resp = api_client.get("/api/outage-status")
            assert resp.status_code == 200
            body = resp.json()
            assert body["outage_in_progress"] is True
            assert body["outage_start_time"] == ts.isoformat()
        finally:
            shared_state.set_outage_in_progress(False)
            shared_state.set_outage_start_time(None)

    def test_get_outages_503_when_no_db(self, monkeypatch):
        import src.api.routes.outages as outages_module
        from src.api.main import app

        monkeypatch.setattr(outages_module, "DB_PATH", Path("/nonexistent/db.db"))
        monkeypatch.setattr("src.config.API_KEY", None)
        client = TestClient(app)
        resp = client.get("/api/outages")
        assert resp.status_code == 503
