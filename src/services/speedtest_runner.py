"""SpeedtestRunner — wraps speedtest-cli, runs a test, and returns a SpeedResult."""

import speedtest  # type: ignore
from datetime import datetime, timezone
from typing import Any, cast

from src.models.speed_result import SpeedResult

class SpeedtestRunner:
    """
    Runs a speed test and returns the results as a SpeedResult dataclass.  
    Raises SpeedtestException on network or server errors.
    """
    
    def run(self) -> SpeedResult:
        """Run the speed test and return the results."""
        try: 
            st = speedtest.Speedtest()
            best: dict[str, Any] = cast(dict[str, Any], st.get_best_server())  # type: ignore[no-untyped-call]
            download_bps = st.download(threads=None)  # type: ignore[no-untyped-call]
            upload_bps = st.upload(threads=None, pre_allocate=True)  # type: ignore[no-untyped-call]

            return SpeedResult(
                timestamp=datetime.now(timezone.utc),
                download_mbps=round(download_bps / 1_000_000, 2),
                upload_mbps=round(upload_bps / 1_000_000, 2),
                ping_ms=round(st.results.ping, 2),
                server_name=str(best.get("sponsor", "Unknown")),
                server_location=f"{best.get('name', '')}, {best.get('country', '')}",
                server_id=int(str(best["id"])) if best.get("id") is not None else None,
            )

        except speedtest.ConfigRetrievalError:
            # Can't reach speedtest.net config endpoint — likely no internet
            raise RuntimeError("Could not reach speedtest.net — check network connectivity.")

        except speedtest.NoMatchedServers:
            # Happens if you manually filter servers and none match
            raise RuntimeError("No speedtest servers matched the selection criteria.")

        except speedtest.SpeedtestHTTPError as e:
            raise RuntimeError(f"HTTP error during speedtest: {e}")

        except speedtest.SpeedtestException as e:
            # Base exception — catches anything else the library raises
            raise RuntimeError(f"Speedtest failed: {e}")