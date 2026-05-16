"""Tests for src/services/sla_monitor.py."""

from __future__ import annotations

import datetime

import pytest

from src.models.speed_result import SpeedResult
from src.services.sla_monitor import SLAMonitor, SLAResult


def _make(
    download: float = 100.0,
    upload: float = 50.0,
    ping: float = 20.0,
    jitter: float | None = None,
    loss: float | None = None,
) -> SpeedResult:
    return SpeedResult(
        download_mbps=download,
        upload_mbps=upload,
        ping_ms=ping,
        jitter_ms=jitter,
        packet_loss_pct=loss,
        server_name="Test Server",
        server_location="Test City",
        timestamp=datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
    )


class TestSLAMonitorDisabled:
    def test_no_thresholds_returns_disabled_result(self) -> None:
        monitor = SLAMonitor()
        result = monitor.check(_make())
        assert result.download_ok is None
        assert result.upload_ok is None
        assert result.ping_ok is None
        assert result.packet_loss_ok is None
        assert result.overall_ok is True

    def test_enabled_false_when_no_thresholds(self) -> None:
        assert not SLAMonitor().enabled


class TestSLAMonitorDownload:
    def test_download_above_threshold_passes(self) -> None:
        monitor = SLAMonitor(min_download_mbps=50.0)
        result = monitor.check(_make(download=100.0))
        assert result.download_ok is True

    def test_download_below_threshold_fails(self) -> None:
        monitor = SLAMonitor(min_download_mbps=50.0)
        result = monitor.check(_make(download=30.0))
        assert result.download_ok is False
        assert result.overall_ok is False

    def test_download_at_threshold_passes(self) -> None:
        monitor = SLAMonitor(min_download_mbps=50.0)
        result = monitor.check(_make(download=50.0))
        assert result.download_ok is True


class TestSLAMonitorUpload:
    def test_upload_above_threshold_passes(self) -> None:
        monitor = SLAMonitor(min_upload_mbps=10.0)
        result = monitor.check(_make(upload=20.0))
        assert result.upload_ok is True

    def test_upload_below_threshold_fails(self) -> None:
        monitor = SLAMonitor(min_upload_mbps=10.0)
        result = monitor.check(_make(upload=5.0))
        assert result.upload_ok is False
        assert result.overall_ok is False


class TestSLAMonitorPing:
    def test_ping_below_max_passes(self) -> None:
        monitor = SLAMonitor(max_ping_ms=50.0)
        result = monitor.check(_make(ping=30.0))
        assert result.ping_ok is True

    def test_ping_above_max_fails(self) -> None:
        monitor = SLAMonitor(max_ping_ms=50.0)
        result = monitor.check(_make(ping=80.0))
        assert result.ping_ok is False
        assert result.overall_ok is False

    def test_ping_at_max_passes(self) -> None:
        monitor = SLAMonitor(max_ping_ms=50.0)
        result = monitor.check(_make(ping=50.0))
        assert result.ping_ok is True


class TestSLAMonitorPacketLoss:
    def test_packet_loss_below_max_passes(self) -> None:
        monitor = SLAMonitor(max_packet_loss_pct=2.0)
        result = monitor.check(_make(loss=1.0))
        assert result.packet_loss_ok is True

    def test_packet_loss_above_max_fails(self) -> None:
        monitor = SLAMonitor(max_packet_loss_pct=2.0)
        result = monitor.check(_make(loss=3.0))
        assert result.packet_loss_ok is False
        assert result.overall_ok is False

    def test_packet_loss_none_returns_none(self) -> None:
        monitor = SLAMonitor(max_packet_loss_pct=2.0)
        result = monitor.check(_make(loss=None))
        assert result.packet_loss_ok is None


class TestSLAMonitorOverall:
    def test_all_pass_returns_overall_ok(self) -> None:
        monitor = SLAMonitor(
            min_download_mbps=50.0,
            min_upload_mbps=10.0,
            max_ping_ms=50.0,
        )
        result = monitor.check(_make(download=100, upload=20, ping=30))
        assert result.overall_ok is True

    def test_one_failure_overall_false(self) -> None:
        monitor = SLAMonitor(
            min_download_mbps=50.0,
            min_upload_mbps=10.0,
            max_ping_ms=50.0,
        )
        result = monitor.check(_make(download=100, upload=20, ping=90))
        assert result.overall_ok is False

    def test_enabled_true_when_threshold_set(self) -> None:
        assert SLAMonitor(min_download_mbps=50.0).enabled


class TestSLAResultDisabled:
    def test_disabled_classmethod(self) -> None:
        result = SLAResult.disabled()
        assert result.overall_ok is True
        assert result.download_ok is None
        assert result.upload_ok is None
        assert result.ping_ok is None
        assert result.packet_loss_ok is None
