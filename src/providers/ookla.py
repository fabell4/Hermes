"""OoklaProvider — speed test via the official Ookla CLI."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess  # nosec B404  # NOSONAR - Required to invoke Ookla CLI executable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src import config
from src.models.speed_result import SpeedResult
from src.providers.base import BaseTestProvider

_log = logging.getLogger(__name__)


class OoklaProvider(BaseTestProvider):
    """Runs a speed test using the official Ookla CLI.

    Security: Uses absolute path to speedtest binary (resolved lazily) to prevent
    PATH manipulation attacks. All subprocess arguments are hardcoded strings with
    no user input injected.
    """

    def __init__(
        self,
        speedtest_path: str | None = None,
        server_id: int | None = None,
    ) -> None:
        """
        Initialize the Ookla provider.

        Args:
            speedtest_path: Optional explicit path to the speedtest binary.
                            If None, resolved from PATH on first use.
            server_id: Optional Ookla server ID to pin tests to a specific server.
                       If None, the CLI selects the nearest server automatically.
        """
        self._speedtest_path: str | None = speedtest_path
        self._path_resolved = speedtest_path is not None
        self._server_id: int | None = server_id

    @property
    def name(self) -> str:
        return "ookla"

    def _get_speedtest_path(self) -> str:
        """Resolve and cache the speedtest binary path.

        Returns:
            Absolute path to the speedtest binary.

        Raises:
            RuntimeError: If the speedtest CLI is not found in PATH.
        """
        if not self._path_resolved:
            speedtest_path = shutil.which("speedtest")
            if speedtest_path is None:
                raise RuntimeError(
                    "Ookla speedtest CLI not found in PATH. "
                    "Install from https://www.speedtest.net/apps/cli"
                )
            self._speedtest_path = speedtest_path
            self._path_resolved = True
            _log.debug("Using speedtest binary at: %s", self._speedtest_path)

        # Type narrowing: after _path_resolved is True, _speedtest_path is str
        if self._speedtest_path is None:  # pragma: no cover
            raise RuntimeError("Speedtest path not resolved.")
        return self._speedtest_path

    def _parse_result(self, data: dict[str, Any], tz: ZoneInfo) -> SpeedResult:
        """Parse Ookla CLI JSON output into a SpeedResult."""
        server = data.get("server", {})
        download_bps = data.get("download", {}).get("bandwidth", 0) * 8
        upload_bps = data.get("upload", {}).get("bandwidth", 0) * 8
        ping_data = data.get("ping", {})
        ping_ms = ping_data.get("latency", 0)
        jitter_ms = ping_data.get("jitter")

        raw_loss = data.get("packetLoss")
        packet_loss_pct = round(float(raw_loss), 2) if raw_loss is not None else None

        server_id_raw = server.get("id")
        server_id = int(server_id_raw) if server_id_raw is not None else None

        return SpeedResult(
            timestamp=datetime.now(tz),
            download_mbps=round(download_bps / 1_000_000, 2),
            upload_mbps=round(upload_bps / 1_000_000, 2),
            ping_ms=round(ping_ms, 2),
            server_name=server.get("name", "Unknown"),
            server_location=f"{server.get('location', '')}, {server.get('country', '')}",
            server_id=server_id,
            jitter_ms=round(jitter_ms, 2) if jitter_ms is not None else None,
            isp_name=data.get("isp"),
            packet_loss_pct=packet_loss_pct,
        )

    def run(self) -> SpeedResult:
        """Execute a single speed test using the Ookla CLI.

        Raises:
            RuntimeError: On timeout, non-zero exit code, or unparseable output.
        """
        try:
            # Security: All arguments are hardcoded strings (no user input).
            # Uses absolute path to prevent PATH injection.
            speedtest_path = self._get_speedtest_path()
            cmd = [
                speedtest_path,
                "--accept-license",
                "--accept-gdpr",
                "--format=json",
            ]
            # Append server pin if configured — validated as positive int by config
            if self._server_id is not None:
                cmd.append(f"--server-id={self._server_id}")

            result = subprocess.run(  # nosec B603  # NOSONAR - No user input, hardcoded args only
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                check=True,
            )

            data: dict[str, Any] = json.loads(result.stdout)

            _tz_name = config.TIMEZONE
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            return self._parse_result(data, _tz)

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Speedtest timed out after 120 seconds.") from exc

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Ookla speedtest CLI not found — check installation."
            ) from exc

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            raise RuntimeError(
                f"Speedtest CLI failed (exit {exc.returncode}): {stderr.strip()}"
            ) from exc

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"Failed to parse speedtest output: {exc}") from exc
