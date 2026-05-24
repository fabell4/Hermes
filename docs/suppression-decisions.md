---
layout: default
title: "Suppression Decisions"
---

# Suppression Comment Decisions

This document records every lint/type suppression comment in the codebase, why it exists,
and why it cannot simply be removed.

---

## Python

### `src/config.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `CORS_ORIGINS` default value | `# NOSONAR` (S5332) | The default value `http://localhost:5173,http://localhost:4173` is a **development-only** default for the local Vite/React dev server. It is never active in production — users set `CORS_ORIGINS` to their own HTTPS domain. The `http://` is localhost-only and poses no cross-site risk. |
| `"OUTAGE_PROBE_HOSTS", ["1.1.1.1:53", ...]` | `# NOSONAR` (S1313) | The three IPs are well-known public DNS resolvers: Cloudflare (1.1.1.1), Google (8.8.8.8), and Quad9 (9.9.9.9). They are the **hardcoded default** probe endpoints for connectivity detection, not internal infrastructure addresses. Users can override them via `OUTAGE_PROBE_HOSTS`. |

### `tests/test_api_ssrf.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `"url": "http://hooks.example.com:8080/webhook"` | `# NOSONAR` (S5332) | Intentional HTTP test vector in `test_http_url_rejected`. The test verifies that the SSRF validator correctly rejects plain `http://` URLs. The `http://` is necessary test input, not production code. |
| `"""ftp:// scheme should be rejected."""` and `"url": "ftp://..."` | `# NOSONAR` (S5332) | Intentional FTP test vectors in `test_ftp_scheme_rejected`. The test verifies that non-HTTP(S) schemes are blocked by the SSRF validator. |
| `assert "ftp://" in response.json()[...]` | `# NOSONAR` (S5332) | Assertion string against a test vector — checks that the rejection reason mentions the blocked scheme. |
| Private IP literals (`10.0.0.1`, `192.168.1.1`, `172.20.0.5`, `169.254.169.254`) | `# NOSONAR` (S1313) | Intentional RFC 1918 / link-local SSRF test vectors. These addresses verify that the SSRF validator blocks private and link-local ranges. They appear only in test payloads and are never used as connection targets. |

### `src/providers/ookla.py`

| Line                    | Suppression                         | Reason |
| ----------------------- | ----------------------------------- | ------ |
| `import subprocess`     | `# nosec B404  # NOSONAR`           | Bandit B404 flags subprocess import as a security risk. This module requires subprocess to invoke the Ookla speedtest CLI binary. No alternative exists for external process execution. Mitigated by: (1) using absolute path resolved via `shutil.which()` (lazy evaluation), (2) hardcoded arguments only (no user input), (3) timeout enforcement. |
| `subprocess.run([...])` | `# nosec B603  # NOSONAR`           | Bandit B603 warns about subprocess call with potential untrusted input. All arguments are hardcoded strings defined in source code — no user input is ever passed to the subprocess call. The command list is: `[speedtest_path, "--accept-license", "--accept-gdpr", "--format=json"]`. The executable path is resolved lazily via `_get_speedtest_path()` which uses `shutil.which()` and caches the result. Tests can override by passing `speedtest_path` to `__init__()`. |

### `src/services/health_server.py`

| Line                           | Suppression                                     | Reason                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------ | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `def do_GET(self)`             | `# noqa: N802  # pylint: disable=invalid-name` | Python's stdlib `BaseHTTPRequestHandler` dispatches incoming HTTP requests by looking up a method named exactly `do_<VERB>` on the handler class. Renaming this method to `do_get` (PEP 8 lowercase) would silently break dispatch — the server would return 501 for every GET request. The uppercase name is a **stdlib contract**, not a style choice.                    |
| `def log_message(self, *args)` | `# type: ignore[override]`                      | The stdlib base class declares `log_message(self, format: str, *args: Any)`. Our override uses `*args: object` to avoid the overly-broad `Any` annotation. mypy correctly flags this as a signature mismatch that cannot be expressed as a proper `@override` without reverting to `Any`.                                                                                  |

### `src/providers/ndt7.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `except Exception` in `_download_sender`, `_upload_receiver`, `_upload_sender` (×3) | `# pylint: disable=broad-exception-caught` | WebSocket send/receive threads run in the background. Any exception that escapes a thread is silently swallowed by the thread runtime with no visibility. The broad catch ensures `stop_event` is always set (preventing the test from hanging) and the websocket is closed cleanly regardless of the failure type. |

### `src/exporters/base_exporter.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `def export_outage_event(self, event: OutageEvent)` | `# noqa: ARG002` | The `event` parameter is intentionally unused in the default no-op implementation. Subclasses that override this method will use it. Renaming to `_event` would break the override contract; a suppression is cleaner than a dummy reference. |

### `src/exporters/csv_exporter.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `except Exception` in `export()` prune block | `# pylint: disable=broad-except` | CSV pruning is non-fatal — if it fails, the just-written data row must not be rolled back. A narrow exception type would silently allow other failure types to propagate and incorrectly report the export as failed. The error is logged with `exc_info=True` for full traceability. |

### `src/exporters/influxdb_exporter.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `from influxdb_client import ...` (×4) | `# type: ignore[import-untyped]` | The `influxdb-client` package does not ship type stubs and is not in `typeshed`. mypy cannot type-check its imports without this suppression. The package itself is well-maintained and functionally correct; the missing stubs are a packaging gap, not a code issue. |

### `src/services/alert_manager.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `except Exception` in `_send_alert_async`, fallback send loop, `send_test_alert` (×3) | `# pylint: disable=broad-exception-caught` | Alert providers can raise any exception (network errors, auth failures, unexpected provider bugs). Allowing an exception to escape would crash the thread-pool worker or the monitoring loop. Each catch logs the full traceback via `exc_info=True`. |

### `src/services/alert_provider_factory.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `except Exception` in each `register_*_provider` function (×4) | `# pylint: disable=broad-except` | Provider constructors validate their configuration (URL, token, etc.) and may raise `ValueError` or other exceptions on bad config. A failure in one provider must not prevent the remaining providers from being registered. The error is logged as a warning so the operator can diagnose misconfiguration. |

### `src/services/outage_detector.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `except Exception` in `get_isp_asn`, `check_bgp_stability`, `check_cloudflare_outage`, `_get_public_ip` (×4) | `# pylint: disable=broad-except` | These methods call external enrichment APIs (RIPE Stat, Cloudflare Radar, ipify). Any network or parsing failure must degrade gracefully — enrichment is best-effort and must never block or crash the outage detection flow. Each catch logs a warning and returns a safe fallback value. |

### `src/api/routes/alerts.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `global _test_alert_last_call` | `# pylint: disable=global-statement` | The test-alert rate limiter tracks the last-call timestamp in a module-level variable. FastAPI does not provide a built-in per-endpoint state store, and introducing a full class or dependency injection for a single float would be over-engineering. The global is intentional and confined to one function. |

### `src/api/routes/outages.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `raise HTTPException(status_code=503, ...)` in `_connect()` | `# NOSONAR` (S8415) | Same pattern as `results.py`: the 503 is raised in a shared `_connect()` helper, not directly inside a route. It **is** documented via `responses=` on every route that calls it. SonarQube cannot trace the exception through the helper function, making this a false positive. |

### `src/result_dispatcher.py`

| Line               | Suppression                                | Reason |
| ------------------ | ------------------------------------------ | ------ |
| `except Exception` in `dispatch()` | `# pylint: disable=broad-exception-caught` | The dispatcher calls every configured exporter in a loop. If one exporter raises, the exception **must** be caught broadly so the remaining exporters still run. Narrowing to a specific exception type would silently swallow failures from exporters that raise something else. This is intentional fan-out error isolation, not laziness. |
| `except Exception` in `dispatch_outage_event()` | `# pylint: disable=broad-exception-caught` | Outage event recording is best-effort. A failure in one exporter must never propagate and interrupt the main scheduling loop. Same rationale as `dispatch()`, but errors are logged as warnings (not errors) since outage event storage is supplementary to the primary speed-test dispatch. |

### `src/main.py`

| Line                    | Suppression                      | Reason |
| ----------------------- | -------------------------------- | ------ |
| `except Exception` (×2) | `# pylint: disable=broad-except` | The scheduler loop must stay alive across any failure. A narrow except would crash the entire background process on any unexpected error (e.g., a transient OS error, an unhandled edge case in a new exporter). Broad catch is the correct approach for a long-running daemon loop. |

### `src/api/routes/trigger.py`

| Line               | Suppression                                | Reason                                                                                                                                                                                                                                                                                    |
| ------------------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `except Exception` | `# pylint: disable=broad-exception-caught` | The trigger endpoint runs a speedtest in a background task. Any exception that escapes would be swallowed by the task runner with no visibility. The broad catch ensures the error is logged and a meaningful response is returned to the caller. |

### `src/api/routes/results.py`

| Line | Suppression | Reason |
| ---- | ----------- | ------ |
| `raise HTTPException(status_code=503, ...)` in `_connect()` | `# NOSONAR` (S8415) | Sonar S8415 requires every raised `HTTPException` to be documented in a route's `responses` parameter. `_connect()` is a shared helper — the 503 **is** documented via `responses=_503` (or `responses={**_503, ...}`) on every route that calls it (`get_results`, `get_latest_result`, `update_note`). Sonar cannot trace the exception through helper functions, making this a false positive. |

---

## TypeScript / Frontend

### `frontend/src/components/SpeedGauge.tsx`

| Line            | Suppression  | Reason                                                                                                                                                                                                                                                                                                                                                            |
| --------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Math.random()` | `// NOSONAR` | SonarQube rule S2245 flags `Math.random()` as a potential weak-randomness security issue. Here it is used exclusively for a needle-jitter animation effect in the UI — it has no involvement in security, authentication, token generation, or any other sensitive context. The hotspot is a false positive. |

---

## What is NOT suppressed (for reference)

The following were investigated and fixed rather than suppressed:

- `_503` response dict in `src/api/routes/results.py` — annotated as `dict[int | str, dict[str, Any]]` to satisfy
  mypy.
- `full_path` parameter in `src/api/main.py` `spa_fallback` — used in a `logger.debug` call rather than suppressed as
  an unused argument.
- `logging.getLogger(__name__)` in `speedtest_runner.py` and `health_server.py` — spurious `# type: ignore` removed;
  `logging.getLogger` is fully typed in typeshed.
