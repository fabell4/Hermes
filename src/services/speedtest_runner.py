"""SpeedtestRunner — wraps speedtest-cli, runs a test, and returns a SpeedResult."""

import logging
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import speedtest

from src import config
from src.models.speed_result import SpeedResult

_log = logging.getLogger(__name__)


def _parse_server_id(raw: object) -> int | None:
    """Return the server id as an int, or None if absent or non-numeric."""
    if raw is None:
        return None
    try:
        return int(str(raw))
    except (ValueError, TypeError):
        _log.warning(
            "Unexpected non-numeric server id from speedtest.net: %r — skipping.", raw
        )
        return None


def _parse_isp(client: object) -> str | None:
    """Return the ISP name from the client dict, or None if unavailable."""
    if not isinstance(client, dict):
        return None
    return str(client.get("isp", "")) or None


def _parse_jitter(raw: object) -> float | None:
    """Return jitter in ms as a float, or None if absent or non-numeric."""
    if raw is None:
        return None
    try:
        return round(float(raw), 2)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        _log.warning("Unexpected jitter value from speedtest.net: %r — skipping.", raw)
        return None


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
            best: dict[str, Any] = cast(dict[str, Any], st.get_best_server())
            download_bps = st.download(threads=None)
            upload_bps = st.upload(threads=None, pre_allocate=True)

            _tz_name = config.TIMEZONE
            try:
                _tz = ZoneInfo(_tz_name)
            except ZoneInfoNotFoundError:
                _tz = ZoneInfo("UTC")

            server_id = _parse_server_id(best.get("id"))
            isp_name = _parse_isp(st.results.client)
            jitter_ms = _parse_jitter(getattr(st.results, "jitter", None))

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
