"""SpeedtestRunner — wraps Ookla CLI, runs a test, and returns a SpeedResult."""

import json
import logging
import shutil
import subprocess  # noqa: S404  # NOSONAR - Required to invoke Ookla CLI executable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src import config
from src.models.speed_result import SpeedResult

_log = logging.getLogger(__name__)


class SpeedtestRunner:
    """
    Runs a speed test using official Ookla CLI and returns results as SpeedResult.
    Retries once on transient failure before raising.
    
    Security: Uses absolute path to speedtest binary (resolved lazily) to prevent
    PATH manipulation attacks.
    """

    def __init__(self, speedtest_path: str | None = None) -> None:
        """
        Initialize runner.
        
        Args:
            speedtest_path: Optional explicit path to speedtest binary.
                           If None, will be resolved from PATH on first use.
                           Used for testing and explicit binary location specification.
        """
        self._speedtest_path: str | None = speedtest_path
        self._path_resolved = speedtest_path is not None
    
    def _get_speedtest_path(self) -> str:
        """
        Resolve and cache the speedtest binary path.
        
        Returns:
            Absolute path to speedtest binary.
            
        Raises:
            RuntimeError: If speedtest CLI not found in PATH.
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
        assert self._speedtest_path is not None
        return self._speedtest_path

    def run(self) -> SpeedResult:
        """Run the speed test, retrying once on transient failure."""
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                return self._attempt()
            except RuntimeError as exc:
                last_exc = exc
                if attempt == 0:
                    _log.warning("Speedtest attempt 1 failed (%s) — retrying.", exc)
        if last_exc is None:  # pragma: no cover
            raise RuntimeError("Speedtest failed with no recorded exception.")
        raise last_exc

    def _attempt(self) -> SpeedResult:
        """Execute a single speed test attempt using Ookla CLI."""
        try:
            # Run speedtest CLI with JSON output and accept license automatically
            # Security: All arguments are hardcoded strings (no user input)
            # Uses absolute path to prevent PATH injection
            speedtest_path = self._get_speedtest_path()
            result = subprocess.run(  # noqa: S603  # NOSONAR - No user input, hardcoded args only
                [
                    speedtest_path,
                    "--accept-license",
                    "--accept-gdpr",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                check=True,
            )

            data: dict[str, Any] = json.loads(result.stdout)

            # Parse timezone
            _tz_name = config.TIMEZONE
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            # Extract values from Ookla JSON format
            # Bandwidth is in bytes/s, multiply by 8 for bits/s
            server = data.get("server", {})
            download_bps = data.get("download", {}).get("bandwidth", 0) * 8
            upload_bps = data.get("upload", {}).get("bandwidth", 0) * 8
            ping_data = data.get("ping", {})
            ping_ms = ping_data.get("latency", 0)
            jitter_ms = ping_data.get("jitter")

            # Parse server_id as int (Ookla returns int, but ensure type safety)
            server_id_raw = server.get("id")
            server_id = int(server_id_raw) if server_id_raw is not None else None

            return SpeedResult(
                timestamp=datetime.now(_tz),
                download_mbps=round(download_bps / 1_000_000, 2),
                upload_mbps=round(upload_bps / 1_000_000, 2),
                ping_ms=round(ping_ms, 2),
                server_name=server.get("name", "Unknown"),
                server_location=f"{server.get('location', '')}, {server.get('country', '')}",
                server_id=server_id,
                jitter_ms=round(jitter_ms, 2) if jitter_ms is not None else None,
                isp_name=data.get("isp"),
            )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Speedtest timed out after 120 seconds.") from exc

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            raise RuntimeError(
                f"Speedtest CLI failed (exit {exc.returncode}): {stderr.strip()}"
            ) from exc

        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"Failed to parse speedtest output: {exc}") from exc

        except FileNotFoundError as exc:
            raise RuntimeError("Speedtest CLI not found — check installation.") from exc
