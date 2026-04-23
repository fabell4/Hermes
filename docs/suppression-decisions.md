# Suppression Comment Decisions

This document records every lint/type suppression comment in the codebase, why it exists,
and why it cannot simply be removed.

---

## Python

### `src/services/speedtest_runner.py`

| Line | Suppression | Reason |
|------|-------------|--------|
| `import speedtest` | `# type: ignore` | `speedtest-cli` ships no type stubs and has no third-party stub package on PyPI. There is no fix available short of replacing the library. |
| `st.get_best_server()` | `# type: ignore[no-untyped-call]` | The speedtest library's methods are entirely unannotated. mypy cannot infer their return types. |
| `st.download(...)` | `# type: ignore[no-untyped-call]` | Same library, same reason. |
| `st.upload(...)` | `# type: ignore[no-untyped-call]` | Same library, same reason. |

### `src/services/health_server.py`

| Line | Suppression | Reason |
|------|-------------|--------|
| `def do_GET(self)` | `# noqa: N802  # pylint: disable=invalid-name` | Python's stdlib `BaseHTTPRequestHandler` dispatches incoming HTTP requests by looking up a method named exactly `do_<VERB>` on the handler class. Renaming this method to `do_get` (PEP 8 lowercase) would silently break dispatch — the server would return 501 for every GET request. The uppercase name is a **stdlib contract**, not a style choice. |
| `def log_message(self, *args)` | `# type: ignore[override]` | The stdlib base class declares `log_message(self, format: str, *args: Any)`. Our override uses `*args: object` to avoid the overly-broad `Any` annotation. mypy correctly flags this as a signature mismatch that cannot be expressed as a proper `@override` without reverting to `Any`. |

### `src/result_dispatcher.py`

| Line | Suppression | Reason |
|------|-------------|--------|
| `except Exception` | `# pylint: disable=broad-exception-caught` | The dispatcher calls every configured exporter in a loop. If one exporter raises, the exception **must** be caught broadly so the remaining exporters still run. Narrowing to a specific exception type would silently swallow failures from exporters that raise something else. This is intentional fan-out error isolation, not laziness. |

### `src/main.py`

| Line | Suppression | Reason |
|------|-------------|--------|
| `except Exception` (×3) | `# pylint: disable=broad-except` | The scheduler loop must stay alive across any failure. A narrow except would crash the entire background process on any unexpected error (e.g., a transient OS error, an unhandled edge case in a new exporter). Broad catch is the correct approach for a long-running daemon loop. |

### `src/api/routes/trigger.py`

| Line | Suppression | Reason |
|------|-------------|--------|
| `except Exception` | `# pylint: disable=broad-exception-caught` | The trigger endpoint runs a speedtest in a background task. Any exception that escapes would be swallowed by the task runner with no visibility. The broad catch ensures the error is logged and a meaningful response is returned to the caller. |

---

## TypeScript / Frontend

### `frontend/src/components/SpeedGauge.tsx`

| Line | Suppression | Reason |
|------|-------------|--------|
| `Math.random()` | `// NOSONAR` | SonarQube rule S2245 flags `Math.random()` as a potential weak-randomness security issue. Here it is used exclusively for a needle-jitter animation effect in the UI — it has no involvement in security, authentication, token generation, or any other sensitive context. The hotspot is a false positive. |

---

## What is NOT suppressed (for reference)

The following were investigated and fixed rather than suppressed:

- `_503` response dict in `src/api/routes/results.py` — annotated as `dict[int | str, dict[str, Any]]` to satisfy mypy.
- `full_path` parameter in `src/api/main.py` `spa_fallback` — used in a `logger.debug` call rather than suppressed as an unused argument.
- `logging.getLogger(__name__)` in `speedtest_runner.py` and `health_server.py` — spurious `# type: ignore` removed; `logging.getLogger` is fully typed in typeshed.
