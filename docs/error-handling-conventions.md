---
layout: default
title: "Error Handling Conventions"
---

# Error Handling Conventions

**Project:** Hermes Speed Monitor  
**Last Updated:** 2026-05-01  
**Purpose:** Document error handling patterns, exception hierarchies, and conventions

---

## Table of Contents

- [Guiding Principles](#guiding-principles)
- [When to Raise vs Log](#when-to-raise-vs-log)
- [Exception Hierarchies](#exception-hierarchies)
- [Exception Wrapping Guidelines](#exception-wrapping-guidelines)
- [Logging Guidelines](#logging-guidelines)
- [Error Recovery Patterns](#error-recovery-patterns)
- [Testing Error Paths](#testing-error-paths)

---

## Guiding Principles

### 1. Fail Fast, Fail Loudly

- Raise exceptions for programming errors and invalid states
- Make problems visible immediately, not silently swallowed
- Use assertions for invariants that should never be violated

**Example:**
```python
def register(self, name: str, exporter: BaseExporter) -> None:
    if not isinstance(exporter, BaseExporter):
        raise TypeError(
            f"Exporter must inherit from BaseExporter, got {type(exporter).__name__}"
        )
```

---

### 2. Be Resilient to External Failures

- Catch and log exceptions from external systems (network, filesystem, databases)
- Continue operation when possible (e.g., one exporter fails, others succeed)
- Implement retry logic for transient failures

**Example:**
```python
try:
    self._prune()
except OSError as e:
    # Pruning failure should not prevent writing new results
    logger.error("Failed to prune CSV file: %s", e, exc_info=True)
```

---

### 3. Provide Actionable Error Messages

- Include context: what failed, why, and how to fix it
- Include relevant values (URLs, file paths, counts)
- Use specific exception types to enable targeted error handling

**Example:**
```python
raise SQLiteLockTimeout(
    f"Database locked for {self.timeout_seconds}s: {self.db_path}. "
    "Check for long-running queries or reduce page_size."
)
```

---

## When to Raise vs Log

### Raise an Exception When:

1. **Programming Error:** Invalid arguments, type mismatches, violated contracts
   ```python
   if not isinstance(data, dict):
       raise TypeError(f"Expected dict, got {type(data).__name__}")
   ```

2. **Unrecoverable Error:** Configuration is invalid, required dependency missing
   ```python
   if not url:
       raise ValueError("Loki URL is required")
   ```

3. **Caller Must Handle:** Error requires specific handling by caller
   ```python
   if response.status_code >= 400:
       response.raise_for_status()  # Caller decides retry logic
   ```

4. **Fatal System Error:** Cannot continue execution (startup failures)
   ```python
   if not API_KEY:
       logger.critical("API_KEY environment variable is required")
       sys.exit(1)
   ```

---

### Log Without Raising When:

1. **Expected Operational Failures:** Network timeouts, temporary unavailability
   ```python
   try:
       response = requests.post(url, json=payload, timeout=5)
   except Timeout:
       logger.warning("Alert webhook timed out (5s): %s", url)
       # Continue execution, alert sending is best-effort
   ```

2. **Non-Fatal Errors:** One component fails but system continues
   ```python
   for name, exporter in self.exporters.items():
       try:
           exporter.export(result)
       except Exception as e:
           logger.error("Exporter '%s' failed: %s", name, e, exc_info=True)
           # Continue dispatching to remaining exporters
   ```

3. **Degraded Functionality:** Feature unavailable but core functionality works
   ```python
   try:
       self._prune()
   except OSError as e:
       logger.warning("CSV pruning failed: %s - file may grow unbounded", e)
       # Write still succeeds
   ```

4. **Validation Warnings:** Input sanitized to safe default
   ```python
   if not isinstance(interval, int) or not (5 <= interval <= 1440):
       logger.warning("Invalid interval %s, using default %d", interval, DEFAULT_INTERVAL)
       interval = DEFAULT_INTERVAL
   ```

---

## Exception Hierarchies

### Standard Library Exceptions

Use built-in exceptions where appropriate:

| Exception | Use Case |
|-----------|----------|
| `ValueError` | Invalid value (wrong range, format, content) |
| `TypeError` | Wrong type passed to function |
| `KeyError` | Missing required key in dict |
| `OSError` | Filesystem, network, or OS-level errors |
| `RuntimeError` | Generic runtime error (avoid if more specific exists) |
| `TimeoutError` | Operation exceeded time limit |

---

### HTTP Exceptions (FastAPI)

| Status Code | Exception | Use Case |
|-------------|-----------|----------|
| 400 | `HTTPException(status_code=400)` | Invalid request payload |
| 401 | `HTTPException(status_code=401)` | Missing authentication |
| 403 | `HTTPException(status_code=403)` | Invalid credentials |
| 404 | `HTTPException(status_code=404)` | Resource not found |
| 429 | `HTTPException(status_code=429)` | Rate limit exceeded |
| 500 | `HTTPException(status_code=500)` | Internal server error |
| 503 | `HTTPException(status_code=503)` | Service unavailable (temporary) |

**Example:**
```python
if not validate_api_key(x_api_key):
    raise HTTPException(status_code=403, detail="Invalid API key.")
```

---

### Custom Exceptions

#### `DispatchError`

**Source:** [src/result_dispatcher.py](../src/result_dispatcher.py)  
**Purpose:** Aggregate multiple exporter failures  
**When to Use:** Dispatcher collected failures from multiple exporters

```python
class DispatchError(Exception):
    """
    Raised when one or more exporters fail during dispatch.
    Contains mapping of exporter names to their exceptions.
    """
    def __init__(self, failures: dict[str, Exception]) -> None:
        self.failures = failures
        super().__init__(f"{len(failures)} exporter(s) failed")
```

**Usage:**
```python
if failures:
    raise DispatchError(failures)
```

---

#### `SQLiteLockTimeout`

**Source:** [src/exporters/sqlite_exporter.py](../src/exporters/sqlite_exporter.py)  
**Purpose:** Specific timeout error with diagnostic context  
**When to Use:** SQLite database locked beyond configured timeout

```python
class SQLiteLockTimeout(Exception):
    """
    Raised when SQLite database is locked for longer than the configured timeout.
    Includes timeout duration and database path for diagnostics.
    """
    def __init__(self, db_path: str, timeout_seconds: int) -> None:
        self.db_path = db_path
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Database locked for {timeout_seconds}s: {db_path}. "
            "Check for long-running queries or reduce page_size."
        )
```

**Usage:**
```python
except sqlite3.OperationalError as e:
    if "database is locked" in str(e):
        raise SQLiteLockTimeout(self.db_path, self.timeout_seconds) from e
    raise
```

---

## Exception Wrapping Guidelines

### When to Wrap Exceptions

Wrap lower-level exceptions with context when:

1. **Adding Business Context:** Low-level error needs domain-specific meaning
   ```python
   except sqlite3.OperationalError as e:
       raise RuntimeError(f"SQLite write failed: {e}") from e
   ```

2. **Abstracting Implementation Details:** Hide internal library from API
   ```python
   except requests.RequestException as e:
       raise RuntimeError(f"Loki push connection error: {e}") from e
   ```

3. **Aggregating Multiple Errors:** Collect failures into single exception
   ```python
   raise DispatchError(failures)
   ```

---

### When NOT to Wrap

Don't wrap exceptions when:

1. **No Added Value:** Wrapping adds no context
   ```python
   # Bad - no context added
   try:
       result = some_operation()
   except Exception as e:
       raise RuntimeError(str(e)) from e
   
   # Good - let it propagate
   result = some_operation()
   ```

2. **Caller Expects Specific Type:** Wrapping breaks caller's error handling
   ```python
   # Bad - caller expects ValueError
   try:
       value = int(input_string)
   except ValueError as e:
       raise RuntimeError(f"Invalid number: {e}") from e
   
   # Good - preserve exception type
   value = int(input_string)
   ```

---

### Always Use `from` for Exception Chaining

Preserve exception chain for debugging:

```python
# Good - preserves traceback
try:
    result = risky_operation()
except ValueError as e:
    raise RuntimeError(f"Operation failed: {e}") from e

# Bad - loses original exception context
except ValueError as e:
    raise RuntimeError(f"Operation failed: {e}")
```

---

## Logging Guidelines

### Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| `DEBUG` | Detailed diagnostic information | Function entry/exit, variable values |
| `INFO` | Significant operational events | Server started, config loaded, test completed |
| `WARNING` | Unexpected but handled events | Validation fallback, retry triggered, non-fatal error |
| `ERROR` | Operation failed but system continues | Exporter failed, alert send failed |
| `CRITICAL` | Fatal error requiring intervention | Startup failure, invalid API key |

---

### Logging Best Practices

#### 1. Use Structured Logging

Include context in log messages:

```python
# Good - includes context
logger.info(
    "Speedtest complete: %.2f Mbps down, %.2f Mbps up, %.0f ms ping",
    result.download_mbps, result.upload_mbps, result.ping_ms
)

# Bad - vague
logger.info("Test complete")
```

---

#### 2. Include Exception Info for Errors

Use `exc_info=True` to include full traceback:

```python
try:
    self._prune()
except OSError as e:
    logger.error("Failed to prune CSV file: %s", e, exc_info=True)
```

---

#### 3. Use Parameterized Logging

Let logging library handle string formatting:

```python
# Good - efficient, proper escaping
logger.info("Loaded config: interval=%d, exporters=%s", interval, exporters)

# Bad - always formats string even if log level disabled
logger.info(f"Loaded config: interval={interval}, exporters={exporters}")
```

---

#### 4. Log at Appropriate Level

```python
# Critical startup failure - CRITICAL
if not API_KEY:
    logger.critical("API_KEY environment variable is required")
    sys.exit(1)

# Expected validation fallback - WARNING
if not isinstance(interval, int):
    logger.warning("Invalid interval %s, using default", interval)

# Unexpected failure in non-critical path - ERROR
try:
    send_alert()
except Exception as e:
    logger.error("Alert failed: %s", e, exc_info=True)

# Normal operation - INFO
logger.info("Speedtest completed successfully")
```

---

#### 5. Avoid Sensitive Data in Logs

Never log secrets, credentials, or PII:

```python
# Bad - logs API key
logger.info("Authenticated with key: %s", api_key)

# Good - logs prefix only
logger.info("Authenticated with key prefix=%.4s", api_key)

# Good - no sensitive data
logger.info("Authentication successful")
```

---

## Error Recovery Patterns

### Pattern 1: Retry with Exponential Backoff

For transient failures (network, temporary unavailability):

```python
import time

def run_with_retry(max_attempts: int = 3) -> SpeedResult:
    """Run speedtest with retry on transient failure."""
    for attempt in range(1, max_attempts + 1):
        try:
            return self._run_once()
        except (TimeoutError, OSError) as e:
            if attempt == max_attempts:
                logger.error("Speedtest failed after %d attempts", max_attempts)
                raise
            
            backoff = 2 ** attempt  # 2s, 4s, 8s
            logger.warning(
                "Speedtest attempt %d failed: %s - retrying in %ds",
                attempt, e, backoff
            )
            time.sleep(backoff)
```

---

### Pattern 2: Fallback to Default

For configuration validation errors:

```python
def _validate_interval(value: Any) -> int:
    """Validate interval, fallback to default if invalid."""
    if not isinstance(value, int) or not (5 <= value <= 1440):
        logger.warning(
            "Invalid interval %s (expected 5-1440), using default %d",
            value, DEFAULT_INTERVAL
        )
        return DEFAULT_INTERVAL
    return value
```

---

### Pattern 3: Partial Success

For batch operations where one failure shouldn't block others:

```python
def dispatch(self, result: SpeedResult) -> None:
    """Dispatch to all exporters, continue on failure."""
    failures: dict[str, Exception] = {}
    
    for name, exporter in self.exporters.items():
        try:
            exporter.export(result)
        except Exception as e:
            logger.error("Exporter '%s' failed: %s", name, e, exc_info=True)
            failures[name] = e
    
    if failures:
        raise DispatchError(failures)
```

---

### Pattern 4: Atomic Operations with Rollback

For operations that must complete fully or not at all:

```python
def save(data: dict) -> None:
    """Save config atomically to prevent corruption."""
    fd, temp_path = tempfile.mkstemp(dir=config_dir, prefix=".runtime_config_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename (POSIX guarantee)
        Path(temp_path).replace(RUNTIME_CONFIG_PATH)
        logger.info("Runtime config saved successfully")
    except Exception as e:
        # Rollback - clean up temp file
        Path(temp_path).unlink(missing_ok=True)
        logger.error("Failed to save config: %s", e)
        raise
```

---

### Pattern 5: Graceful Degradation

For non-critical features:

```python
def export(self, result: SpeedResult) -> None:
    """Export to CSV, continue even if pruning fails."""
    # Critical: Write new result
    with open(self.path, "a", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(result.to_dict())
    
    # Non-critical: Prune old results
    try:
        self._prune()
    except OSError as e:
        logger.warning("CSV pruning failed: %s - file may grow unbounded", e)
        # Continue - write succeeded
```

---

## Testing Error Paths

### Test Every Exception Path

```python
def test_invalid_api_key_raises_403():
    """Verify 403 response for invalid API key."""
    response = client.get(
        "/api/config",
        headers={"X-Api-Key": "invalid-key"}
    )
    assert response.status_code == 403
    assert "Invalid API key" in response.json()["detail"]
```

---

### Test Error Messages

```python
def test_loki_url_validation_error_message():
    """Verify error message includes actionable guidance."""
    with pytest.raises(ValueError) as exc_info:
        LokiExporter(url="", job="test")
    
    assert "Loki URL is required" in str(exc_info.value)
```

---

### Test Exception Chaining

```python
def test_sqlite_write_failure_chains_exception():
    """Verify original exception is preserved in chain."""
    with pytest.raises(RuntimeError) as exc_info:
        exporter.export(mock_result)
    
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, sqlite3.Error)
```

---

### Test Partial Failures

```python
def test_dispatcher_continues_after_exporter_failure(mocker):
    """Verify dispatcher continues when one exporter fails."""
    mock_csv = mocker.Mock(spec=BaseExporter)
    mock_sqlite = mocker.Mock(spec=BaseExporter)
    mock_sqlite.export.side_effect = RuntimeError("DB locked")
    
    dispatcher.register("csv", mock_csv)
    dispatcher.register("sqlite", mock_sqlite)
    
    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(mock_result)
    
    # CSV succeeded, SQLite failed
    mock_csv.export.assert_called_once()
    assert "sqlite" in exc_info.value.failures
    assert "csv" not in exc_info.value.failures
```

---

### Test Retry Logic

```python
def test_speedtest_retries_on_timeout(mocker):
    """Verify speedtest retries once on timeout."""
    mock_run = mocker.patch.object(
        runner, "_run_once",
        side_effect=[TimeoutError("Test timed out"), mock_result]
    )
    
    result = runner.run()
    
    assert mock_run.call_count == 2
    assert result == mock_result
```

---

## Anti-Patterns to Avoid

### ❌ Bare `except:`

Never catch all exceptions without specifying type:

```python
# Bad - catches KeyboardInterrupt, SystemExit, etc.
try:
    risky_operation()
except:
    logger.error("Something failed")

# Good - catch specific exceptions
try:
    risky_operation()
except (ValueError, OSError) as e:
    logger.error("Operation failed: %s", e)
```

---

### ❌ Swallowing Exceptions Silently

Don't ignore exceptions without logging:

```python
# Bad - silent failure
try:
    optional_cleanup()
except Exception:
    pass

# Good - log the failure
try:
    optional_cleanup()
except Exception as e:
    logger.warning("Cleanup failed (non-fatal): %s", e)
```

---

### ❌ Raising Generic `Exception`

Use specific exception types:

```python
# Bad - too generic
if not url:
    raise Exception("URL missing")

# Good - specific type
if not url:
    raise ValueError("Loki URL is required")
```

---

### ❌ Logging Then Raising

Don't log and raise - let caller decide:

```python
# Bad - logs at ERROR then raises (caller might log again)
try:
    result = operation()
except ValueError as e:
    logger.error("Operation failed: %s", e)
    raise

# Good - just raise, let caller log
result = operation()
```

**Exception:** Logging at WARNING or INFO before raising is acceptable for context.

---

### ❌ Modifying Exception Message Without Context

Don't lose original error:

```python
# Bad - loses original error details
except requests.RequestException as e:
    raise RuntimeError("Request failed")

# Good - preserves original error and adds context
except requests.RequestException as e:
    raise RuntimeError(f"Loki push failed: {e}") from e
```

---

## Related Documentation

- [Error Message Reference](error-messages.md) — Complete error catalog with troubleshooting
- [Error Catalog](error-catalog.md) — Errors by module with causes and remediation
- [Architecture](architecture.md) — System design and error boundaries
- [Testing Strategy](../README.md#testing) — Test coverage and strategy

---

## Document History

- **2026-05-01:** Initial documentation (M3 from ERROR-HANDLING-REVIEW.md)
