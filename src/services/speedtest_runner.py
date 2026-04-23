"""SpeedtestRunner — wraps speedtest-cli, runs a test, and returns a SpeedResult."""

import logging
import os
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import speedtest  # type: ignore

from src.models.speed_result import SpeedResult

_log = logging.getLogger(__name__)


class SpeedtestRunner:
    """
    Runs a speed test and returns the results as a SpeedResult dataclass.
    Retries once on transient failure before raising.
    """

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
        """Execute a single speed test attempt."""
        try:
            st = speedtest.Speedtest()
            best: dict[str, Any] = cast(  # type: ignore[no-untyped-call]
                dict[str, Any], st.get_best_server()
            )
            download_bps = st.download(threads=None)  # type: ignore[no-untyped-call]
            upload_bps = st.upload(threads=None, pre_allocate=True)  # type: ignore[no-untyped-call]

            _tz_name = os.getenv("TZ", "UTC")
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            # --- Defensive parsing of fields from the external speedtest.net response ---
            # Any of these may be absent, null, or an unexpected type on schema changes.
            _raw_id = best.get("id")
            server_id: int | None = None
            if _raw_id is not None:
                try:
                    server_id = int(str(_raw_id))
                except (ValueError, TypeError):
                    _log.warning(
                        "Unexpected non-numeric server id from speedtest.net: %r — skipping.",
                        _raw_id,
                    )

            _client = st.results.client
            isp_name: str | None = (
                str(_client.get("isp", "")) or None
                if isinstance(_client, dict)
                else None
            )

            _raw_jitter = getattr(st.results, "jitter", None)
            jitter_ms: float | None = None
            if _raw_jitter is not None:
                try:
                    jitter_ms = round(float(_raw_jitter), 2)
                except (ValueError, TypeError):
                    _log.warning(
                        "Unexpected jitter value from speedtest.net: %r — skipping.",
                        _raw_jitter,
                    )

            return SpeedResult(
                timestamp=datetime.now(_tz),
                download_mbps=round(float(download_bps) / 1_000_000, 2),
                upload_mbps=round(float(upload_bps) / 1_000_000, 2),
                ping_ms=round(float(st.results.ping), 2),
                server_name=str(best.get("sponsor", "Unknown")),
                server_location=f"{best.get('name', '')}, {best.get('country', '')}",
                server_id=server_id,
                jitter_ms=jitter_ms,
                isp_name=isp_name,
            )

        except speedtest.ConfigRetrievalError as exc:
            raise RuntimeError(
                "Could not reach speedtest.net — check network connectivity."
            ) from exc

        except speedtest.NoMatchedServers as exc:
            raise RuntimeError(
                "No speedtest servers matched the selection criteria."
            ) from exc

        except speedtest.SpeedtestHTTPError as e:
            raise RuntimeError(f"HTTP error during speedtest: {e}") from e

        except speedtest.SpeedtestException as e:
            raise RuntimeError(f"Speedtest failed: {e}") from e
