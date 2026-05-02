---
layout: default
title: "Test Coverage Review"
---

# Hermes — Test Coverage Gaps Review

**Review Date:** 2026-04-30  
**Current Coverage:** 91.36% (Python backend), unknown (TypeScript frontend)  
**Test Count:** 355 tests (Python), 12 tests (TypeScript)  
**Goal:** Identify and document test coverage gaps before v1.0 release

---

## Executive Summary

The Hermes project has a **strong test foundation** with 355 Python tests achieving 91.36%
backend coverage. However, several **critical gaps** exist that should be addressed before v1.0:

### High Priority Issues

1. **Alert Provider Factory** — 66% coverage (lowest module)
2. **ResourceWarnings** — 16 unclosed database warnings in test suite
3. **Frontend Coverage** — Only 3 test files, 12 tests total; major components untested
4. **Error Path Coverage** — Missing tests for several exception handlers
5. **Integration Tests** — No integration or end-to-end tests

### Coverage by Module (Python Backend)

| Module | Coverage | Missing Lines | Priority |
|--------|----------|--------------|----------|
| `alert_provider_factory.py` | **66%** | 66, 70-71, 95-110, 131-152, 174-186 | **HIGH** |
| `main.py` | **83%** | 125-149, 159, 161, 167-172, 337, 349-356, 368-392, 403-409, 472-473 | **HIGH** |
| `runtime_config.py` | **86%** | 39, 63, 79, 93, 105-106, 119, 153-154, 208-217, 233-246, 264-265 | **MEDIUM** |
| `alert_providers.py` | **86%** | 41, 45-49, 85, 142, 181-183, 213, 240, 256-260, 306, 321 | **MEDIUM** |
| `config.py` | **89%** | 33-37, 44, 55, 73-77 | **LOW** |
| `prometheus_exporter.py` | **86%** | 52, 60-66 | **LOW** |
| `csv_exporter.py` | **92%** | 97-98, 133-136, 149 | **LOW** |
| `api/main.py` | **91%** | 76-80, 181-182 | **LOW** |
| `api/routes/alerts.py` | **94%** | 74, 79, 89, 147, 422-427 | **LOW** |
| `api/routes/trigger.py` | **91%** | 86, 122-126 | **LOW** |

### Frontend Coverage Gaps

| Component | Tested? | Priority | Notes |
|-----------|---------|----------|-------|
| `SpeedGauge.tsx` | ✅ Yes | N/A | 4 test cases |
| `CountdownTimer.tsx` | ✅ Yes | N/A | 4 test cases |
| `api.ts` | ✅ Yes | N/A | 4 test cases |
| `Layout.tsx` | ❌ No | **HIGH** | Version check, navigation, update banner |
| `Dashboard.tsx` | ❌ No | **HIGH** | Main page integration |
| `Settings.tsx` | ❌ No | **HIGH** | Config updates, alert setup |
| `SpeedChart.tsx` | ❌ No | **MEDIUM** | Chart rendering, data handling |
| `ResultsTable.tsx` | ❌ No | **MEDIUM** | Pagination, sorting |
| `HermesContext.tsx` | ❌ No | **MEDIUM** | State management |
| `App.tsx` | ❌ No | **LOW** | Routing setup |

**Coverage Estimate:** ~25% of frontend components have tests.

---

## Detailed Gap Analysis

### H1: Alert Provider Factory (66% Coverage) — **HIGH PRIORITY**

**Location:** `src/services/alert_provider_factory.py`  
**Missing Lines:** 66, 70-71, 95-110, 131-152, 174-186  
**Impact:** Critical alerting infrastructure

#### Missing Test Scenarios

1. **Provider Initialization Failures** (Lines 66-186)

   ```python
   # Untested error paths in register_*_provider functions
   except Exception as e:
       logger.warning("Could not initialize webhook alert provider: %s", e)
   ```

   - ❌ No tests for invalid Gotify URLs
   - ❌ No tests for malformed ntfy topics
   - ❌ No tests for Apprise URL validation failures
   - ❌ No tests for webhook URL scheme validation

2. **require_enabled Flag** (Multiple functions)

   ```python
   if require_enabled and not webhook_config.get("enabled", False):
       return
   ```

   - ❌ No tests verify `require_enabled=True` blocks disabled providers
   - ❌ No tests for `require_enabled=False` (default) allowing all configured providers

3. **Missing Configuration Scenarios**
   - ❌ Gotify without token
   - ❌ ntfy without topic
   - ❌ Apprise without URL
   - ❌ Partially configured providers (URL present, token missing)

#### Recommended Tests

**Test File:** `tests/test_alert_provider_factory.py` (new file)

```python
def test_register_webhook_provider_skips_when_require_enabled_true()
def test_register_webhook_provider_accepts_disabled_when_require_enabled_false()
def test_register_gotify_provider_raises_on_invalid_url()
def test_register_ntfy_provider_skips_when_topic_missing()
def test_register_apprise_provider_handles_initialization_error()
def test_register_all_providers_continues_on_partial_failure()
def test_register_all_providers_with_require_enabled_filters()
```

**Estimated Tests:** 15-20 new tests  
**Complexity:** Low-Medium

---

### H2: Main Loop and Startup (83% Coverage) — **HIGH PRIORITY**

**Location:** `src/main.py`  
**Missing Lines:** 125-149, 159, 161, 167-172, 337, 349-356, 368-392, 403-409, 472-473  
**Impact:** Core application lifecycle

#### Main Loop — Missing Test Scenarios

1. **Build Alert Manager** (Lines 125-149)

   ```python
   # Only register providers if alerting is enabled
   if alert_config.get("enabled", False) or failure_threshold > 0:
       register_all_providers(manager, ...)
   ```

   - ❌ No test for `enabled=False` with `failure_threshold=0` (providers not registered)
   - ❌ No test for `enabled=True` triggering provider registration
   - ❌ No test for threshold minimum enforcement (`max(1, failure_threshold)`)

2. **Update Alert Providers** (Lines 159-172)

   ```python
   def update_alert_providers(manager: AlertManager, alert_config: dict) -> None:
       if "failure_threshold" in alert_config:
           manager.failure_threshold = max(1, alert_config["failure_threshold"])
   ```

   - ❌ No test for runtime alert config updates
   - ❌ No test for clearing and re-registering providers
   - ❌ No test for failure threshold validation (minimum 1)

3. **Development Mode Logging** (Lines 407-409)

   ```python
   if config.APP_ENV == "development":
       logger.critical("Speedtest failure in development mode")
   ```

   - ❌ No test verifies critical log in development
   - ❌ No test verifies log absence in production

4. **Environment Validation** (Lines 368-392)

   ```python
   def _validate_environment() -> None:
       """Warn about misconfigured or unreachable services at startup."""
   ```

   - ❌ No tests for Loki endpoint validation warnings
   - ❌ No tests for timeout/connection/HTTP errors

5. **Main Loop Initialization** (Lines 472-473)

   ```python
   if last_paused:
       scheduler.pause_job("speedtest_run")
   ```

   - ❌ No test for restoring paused state on startup
   - ❌ No test for scheduler state persistence across restarts

#### Main Loop — Recommended Tests

**Test File:** `tests/test_main.py` (add to existing)

```python
def test_build_alert_manager_skips_providers_when_disabled()
def test_build_alert_manager_enforces_minimum_threshold()
def test_update_alert_providers_clears_and_re_registers()
def test_update_alert_providers_updates_threshold()
def test_update_alert_providers_updates_cooldown()
def test_run_once_logs_critical_in_development()
def test_validate_environment_warns_on_loki_timeout()
def test_validate_environment_warns_on_loki_connection_error()
def test_main_loop_restores_paused_state()
```

**Estimated Tests:** 12-15 new tests  
**Complexity:** Medium

---

### H3: Runtime Config Edge Cases (86% Coverage) — **MEDIUM PRIORITY**

**Location:** `src/runtime_config.py`  
**Missing Lines:** 39, 63, 79, 93, 105-106, 119, 153-154, 208-217, 233-246, 264-265  
**Impact:** Configuration persistence reliability

#### Runtime Config — Missing Test Scenarios

1. **Load Validation** (Lines 39, 63, 79, 93, 105-106, 119)

   ```python
   if not isinstance(data, dict):
       logger.warning("Runtime config is not a dict, resetting to defaults.")
       return {}
   ```

   - ❌ No test for non-dict JSON (e.g., array, string)
   - ❌ No test for invalid interval types (non-integer)
   - ❌ No test for out-of-range intervals (negative, zero, > 10080)
   - ❌ No test for invalid exporter lists (non-list, list of non-strings)

2. **Save Error Handling** (Lines 153-154)

   ```python
   except OSError as cleanup_error:
       logger.warning("Failed to clean up temp file %s: %s", temp_path, cleanup_error)
   ```

   - ❌ No test for temp file cleanup failure (e.g., permission denied)
   - ❌ No test for atomic rename failure

3. **Alert Config Helpers** (Lines 208-217, 233-246, 264-265)

   ```python
   def get_alert_config() -> dict:
       # Multiple fallback layers
   ```

   - ❌ No test for `get_alert_config()` with missing runtime file
   - ❌ No test for `set_alert_config()` with invalid provider names
   - ❌ No test for partial alert config updates (only some fields)

#### Runtime Config — Recommended Tests

**Test File:** `tests/test_runtime_config.py` (add to existing)

```python
def test_load_resets_on_non_dict_json()
def test_load_validates_interval_range()
def test_load_validates_exporter_list_type()
def test_save_handles_temp_file_cleanup_error()
def test_get_alert_config_falls_back_to_env_when_file_missing()
def test_set_alert_config_partial_update_preserves_other_fields()
```

**Estimated Tests:** 8-10 new tests  
**Complexity:** Low-Medium

---

### H4: Alert Provider Error Paths (86% Coverage) — **MEDIUM PRIORITY**

**Location:** `src/services/alert_providers.py`  
**Missing Lines:** 41, 45-49, 85, 142, 181-183, 213, 240, 256-260, 306, 321  
**Impact:** Alert reliability under error conditions

#### Alert Provider Error Paths — Missing Test Scenarios

1. **Webhook Provider URL Validation** (Lines 41, 45-49)

   ```python
   if not url:
       raise ValueError("Webhook URL cannot be empty")
   parsed = urlparse(url)
   if parsed.scheme not in ("http", "https"):
       raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
   ```

   - ✅ Tested: Empty URL rejection
   - ✅ Tested: Invalid scheme rejection
   - ❌ **Missing:** Tests for edge cases like `ftp://`, `file://`, `javascript:`

2. **Gotify Initialization** (Lines 85, 142)

   ```python
   if not (url and token):
       raise ValueError("Gotify URL and token are required")
   ```

   - ❌ No test for missing URL (only token provided)
   - ❌ No test for missing token (only URL provided)
   - ❌ No test for both missing

3. **ntfy Token Authorization** (Lines 181-183, 213)

   ```python
   if self.token:
       headers["Authorization"] = f"Bearer {self.token}"
   ```

   - ❌ No test verifies Bearer token header is set when token provided
   - ❌ No test verifies header is absent when token is None/empty

4. **Apprise Request Failure** (Lines 240, 256-260, 306, 321)

   ```python
   except requests.exceptions.RequestException as e:
       logger.error("Failed to send Apprise alert to %s: %s", endpoint, e)
       raise
   ```

   - ❌ No test for Apprise timeout
   - ❌ No test for Apprise connection error
   - ❌ No test for Apprise HTTP 4xx/5xx errors

#### Alert Provider Error Paths — Recommended Tests

**Test File:** `tests/test_alert_providers.py` (add to existing)

```python
def test_webhook_provider_rejects_ftp_scheme()
def test_gotify_provider_raises_when_url_missing()
def test_gotify_provider_raises_when_token_missing()
def test_ntfy_provider_includes_bearer_token_when_set()
def test_ntfy_provider_omits_auth_header_when_no_token()
def test_apprise_provider_raises_on_timeout()
def test_apprise_provider_raises_on_connection_error()
def test_apprise_provider_raises_on_http_500()
```

**Estimated Tests:** 10-12 new tests  
**Complexity:** Low

---

### H5: Frontend Component Tests — **HIGH PRIORITY**

**Current State:** 12 tests across 3 files; ~75% of components untested

#### Missing Test Coverage

1. **Layout.tsx** — **HIGH PRIORITY**
   - ❌ Version display
   - ❌ Update available banner
   - ❌ Navigation menu rendering
   - ❌ Mobile responsive menu toggle
   - ❌ Active route highlighting

2. **Dashboard.tsx** — **HIGH PRIORITY**
   - ❌ Data fetching on mount
   - ❌ Loading state display
   - ❌ Error state handling
   - ❌ Stat card rendering with real data
   - ❌ Chart integration
   - ❌ "Run Now" button interaction

3. **Settings.tsx** — **HIGH PRIORITY**
   - ❌ Config form rendering
   - ❌ Interval slider validation
   - ❌ Exporter toggles
   - ❌ Alert provider configuration
   - ❌ Form submission
   - ❌ Success/error toast notifications
   - ❌ Test alert button

4. **SpeedChart.tsx** — **MEDIUM PRIORITY**
   - ❌ Chart renders with data
   - ❌ Empty state when no data
   - ❌ Tooltip formatting
   - ❌ Time range filtering (if implemented)
   - ❌ Responsive sizing

5. **ResultsTable.tsx** — **MEDIUM PRIORITY**
   - ❌ Table renders with results
   - ❌ Pagination controls
   - ❌ Page navigation
   - ❌ Empty state display
   - ❌ ISP column display
   - ❌ Timestamp formatting

6. **HermesContext.tsx** — **MEDIUM PRIORITY**
   - ❌ Context provider initialization
   - ❌ State updates
   - ❌ API polling mechanism
   - ❌ Error handling
   - ❌ Health check updates

#### Frontend Components — Recommended Tests

**New Test Files:**

```typescript
// frontend/src/test/Layout.test.tsx
describe('Layout', () => {
  it('renders version number')
  it('shows update banner when newer version available')
  it('hides update banner when up to date')
  it('highlights active navigation item')
  it('toggles mobile menu on button click')
})

// frontend/src/test/Dashboard.test.tsx
describe('Dashboard', () => {
  it('fetches health and results on mount')
  it('shows loading spinner while fetching')
  it('displays error message on fetch failure')
  it('renders stat cards with latest result')
  it('triggers test on Run Now button click')
  it('disables Run Now button when test running')
})

// frontend/src/test/Settings.test.tsx
describe('Settings', () => {
  it('loads current config on mount')
  it('validates interval within bounds')
  it('toggles exporter checkboxes')
  it('submits config updates')
  it('shows success toast on save')
  it('shows error toast on save failure')
  it('sends test alert on button click')
  it('throttles test alert button (rate limit)')
})

// frontend/src/test/SpeedChart.test.tsx
describe('SpeedChart', () => {
  it('renders chart with data points')
  it('shows empty state when no data')
  it('formats tooltip correctly')
})

// frontend/src/test/ResultsTable.test.tsx
describe('ResultsTable', () => {
  it('renders table rows from results')
  it('shows pagination controls')
  it('navigates pages')
  it('shows empty state')
})

// frontend/src/test/HermesContext.test.tsx
describe('HermesContext', () => {
  it('provides initial state')
  it('polls health endpoint')
  it('updates state on health change')
  it('handles API errors gracefully')
})
```

**Estimated Tests:** 40-50 new tests  
**Complexity:** Medium-High  
**Estimated Effort:** 8-12 hours

---

### H6: Config Module (89% Coverage) — **LOW PRIORITY**

**Location:** `src/config.py`  
**Missing Lines:** 33-37, 44, 55, 73-77  
**Impact:** Configuration defaults and validation

#### Config Module — Missing Test Scenarios

1. **API Key Validation** (Lines 73-77)

   ```python
   if API_KEY is not None and len(API_KEY) < 32:
       logging.error("API_KEY must be at least 32 characters...")
       raise SystemExit(1)
   ```

   - ❌ **Cannot test:** SystemExit on short API key (requires subprocess)
   - ℹ️ **Justification:** This is a startup-time guard; testing would require spawning subprocess with env var

2. **Helper Function Defaults** (Lines 33-37, 44, 55)

   ```python
   def _get_int(key: str, default: int) -> int:
       value = os.getenv(key)
       if value is None:
           return default  # <-- Line 33-35
   ```

   - ❌ No explicit tests for helper functions (`_get_int`, `_get_bool`, `_get_csv_list`)
   - ℹ️ **Justification:** These are implicitly tested via config vars; explicit tests would be redundant

#### Recommendation

**Decision:** DEFER — Lines 73-77 cannot be tested without subprocess isolation; lines 33-37,
44, 55 are sufficiently covered by indirect tests.

**Alternative:** Add integration test in `tests/test_config.py` that spawns subprocess to verify startup failure:

```python
def test_api_key_length_validation_causes_startup_failure():
    """Verify that short API_KEY causes SystemExit(1)."""
    env = os.environ.copy()
    env["API_KEY"] = "short"
    result = subprocess.run(
        [sys.executable, "-c", "import src.config"],
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert b"API_KEY must be at least 32 characters" in result.stderr
```

**Estimated Tests:** 1 subprocess test (optional)  
**Complexity:** Low  
**Priority:** LOW — Deferred to v1.1

---

### H7: ResourceWarnings — Unclosed Databases — **MEDIUM PRIORITY**

**Observation:** 16 `ResourceWarning: unclosed database` warnings during test runs

**Affected Tests:**

- `test_api_results.py::test_results_*` — Multiple warnings
- `test_api_ssrf.py::test_empty_url_accepted` — 7 warnings
- `test_api_trigger.py::test_run_test_no_loki_when_url_not_set` — 1 warning

**Root Cause:**

The `/api/results` endpoint in `src/api/routes/results.py` uses SQLite connections with
context managers, but SQLite's `Connection.__exit__` method **does NOT close the connection** —
it only commits or rolls back transactions.

```python
# Current code (lines 59-68)
with _connect() as conn:  # <-- __exit__ does NOT call close()
    total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    # Connection left open until garbage collection
```

From Python documentation:
> "The `Connection` object can be used as a context manager that automatically commits or
> rolls back open transactions when leaving the body of the context manager. If there is an
> exception, the transaction is rolled back; otherwise, the transaction is committed."
>
> **Note:** The context manager does NOT close the connection.

**Impact:**

- **Tests pass** but leave connections open until garbage collection
- **Not a critical production issue** (connections are eventually garbage collected)
- **Test suite cleanliness** — warnings pollute test output
- **Best practice violation** — connections should be explicitly closed

**Fix:**

Use `contextlib.closing()` to ensure connections are closed, or add explicit `.close()` calls:

**Option 1: Using `contextlib.closing()` (recommended)**

```python
from contextlib import closing

@router.get("/results", responses=_503)
def get_results(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> ResultsPage:
    """Return paginated results, newest first."""
    with closing(_connect()) as conn:  # <-- closing() ensures .close() is called
        total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()

    return ResultsPage(
        results=[SpeedResultSchema(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
```

**Option 2: Explicit `.close()` with try/finally**

```python
@router.get("/results", responses=_503)
def get_results(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> ResultsPage:
    """Return paginated results, newest first."""
    conn = _connect()
    try:
        total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM results ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        
        return ResultsPage(
            results=[SpeedResultSchema(**dict(r)) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        conn.close()
```

**Files to Update:**

- `src/api/routes/results.py` — 2 endpoint functions (`get_results`, `get_latest_result`)

**Verification:**
After fix, run tests with warnings as errors:

```bash
pytest tests/test_api_results.py -W error::ResourceWarning
```

**Estimated Effort:** 20 minutes  
**Priority:** MEDIUM  
**Conflict Check:** ✅ No conflict with modernization review (SQLiteExporter already uses proper patterns)

---

### H8: Integration and End-to-End Tests — **MEDIUM PRIORITY**

**Current State:** **NONE**

All existing tests are **unit tests** or **API endpoint tests**. No integration or end-to-end tests exist.

#### Missing Integration Test Scenarios

1. **Full Speedtest → Export → Alert Flow**
   - Speedtest runs → Result dispatched → All exporters receive data → Alert triggered on failure
   - Currently tested in isolation; never tested end-to-end

2. **Runtime Config Persistence Across Restart**
   - Set interval via API → Shutdown → Restart → Verify interval restored
   - Partially tested but not in full lifecycle

3. **Alert Flow from Failure to Recovery**
   - N consecutive failures → Alert sent → Success → Alert cleared → No re-alert on next failure
   - Currently tested via unit tests; never tested with real scheduler

4. **Multi-Exporter Failure Handling**
   - CSV succeeds, SQLite fails, Prometheus succeeds → Verify partial success handling
   - Currently tested via mock; never tested with real file I/O

5. **API + Scheduler Interaction**
   - Trigger test via API while scheduler is running → Verify lock prevents overlap
   - Currently tested via mock; never tested with real BackgroundScheduler

#### Recommended Integration Tests

**New Test File:** `tests/test_integration.py`

```python
"""Integration tests — multi-component interactions."""

def test_full_speedtest_to_csv_export_flow(tmp_path, monkeypatch):
    """Run real speedtest, dispatch to CSV, verify file contents."""
    # Configure CSV exporter with temp directory
    # Mock Ookla speedtest CLI to return predictable result
    # Run scheduler once
    # Verify CSV contains result row

def test_alert_triggered_after_threshold_consecutive_failures(monkeypatch):
    """Simulate N failures, verify alert sent, then success clears state."""
    # Mock Ookla speedtest CLI to fail N times
    # Run scheduler N times
    # Verify alert provider received notification
    # Mock Ookla speedtest CLI to succeed
    # Run scheduler once
    # Verify alert state cleared

def test_api_config_update_changes_scheduler_interval(monkeypatch):
    """Update interval via API, verify scheduler job updated."""
    # Start scheduler with 60-minute interval
    # PUT /api/config with interval=30
    # Verify scheduler job trigger updated to 30 minutes

def test_concurrent_api_trigger_blocks_scheduler_overlap(monkeypatch):
    """Verify API trigger acquires lock, blocking scheduler run."""
    # Start scheduler
    # Trigger via API (hold lock)
    # Attempt scheduler run (should skip due to lock)
    # Verify only one test ran
```

**Estimated Tests:** 8-12 integration tests  
**Complexity:** Medium-High  
**Estimated Effort:** 6-10 hours  
**Priority:** MEDIUM — Recommended for v1.1

---

## Resource Warnings Summary

**Issue:** 16 `ResourceWarning: unclosed database` warnings during test runs  
**Root Cause:** SQLite connections in `src/api/routes/results.py` not using context managers  
**Fix:** Convert 3 connection usages to `with` statements  
**Impact:** Test cleanliness; no production impact  
**Priority:** MEDIUM

**Quick Fix:**

```python
# src/api/routes/results.py — Line 32, 64, 78
# Replace all occurrences:
conn = sqlite3.connect(db_path)
# With:
with sqlite3.connect(db_path) as conn:
```

---

## Test Metrics Summary

### Python Backend

| Metric | Value |
|--------|-------|
| **Total Tests** | 355 |
| **Coverage** | 91.36% |
| **Modules <90%** | 7 modules |
| **Lowest Coverage** | 66% (alert_provider_factory.py) |
| **Statements** | 1,588 total, 145 missed |
| **Test Files** | 25 files |

### TypeScript Frontend

| Metric | Value |
|--------|-------|
| **Total Tests** | 12 |
| **Coverage** | ~25% (estimated) |
| **Components Tested** | 3 of 12 (25%) |
| **Test Files** | 3 files |

### Overall Project

| Metric | Value |
|--------|-------|
| **Total Tests** | 367 (355 Python + 12 TypeScript) |
| **Estimated Combined Coverage** | ~70-75% |
| **Test Execution Time** | 21.5s (Python), 1.75s (TypeScript) |

---

## Recommendations

### Before v1.0 Release (Required)

1. ✅ **Fix ResourceWarnings** — 15 minutes
   - Convert SQLite connections to context managers in `results.py`

2. ✅ **Alert Provider Factory Tests** — 3-4 hours
   - Add 15-20 tests for `alert_provider_factory.py`
   - Target: 90%+ coverage

3. ⚠️ **Main Loop Tests** — 2-3 hours
   - Add 12-15 tests for `main.py` untested paths
   - Focus on alert manager initialization and update functions
   - Target: 90%+ coverage

4. ⚠️ **Frontend Core Tests** — 6-8 hours
   - Add tests for Layout, Dashboard, Settings (high-value components)
   - Target: 50%+ frontend coverage

**Estimated Total Effort:** 12-16 hours

### After v1.0 Release (v1.1 Candidates)

1. **Frontend Comprehensive Tests** — 8-12 hours
   - Test all remaining components
   - Target: 80%+ frontend coverage

2. **Integration Tests** — 6-10 hours
   - Add `test_integration.py` with 8-12 tests
   - Test multi-component flows

3. **Runtime Config Edge Cases** — 2-3 hours
   - Add 8-10 tests for `runtime_config.py`
   - Target: 95%+ coverage

4. **Alert Provider Error Paths** — 2-3 hours
   - Add 10-12 tests for `alert_providers.py`
   - Target: 95%+ coverage

**Estimated Total Effort:** 18-28 hours

---

## Decision: v1.0 Gate Status

### Required Before v1.0

- ✅ **Fix ResourceWarnings** — MUST FIX (15 min)
- ✅ **Alert Provider Factory Tests** — MUST ADD (3-4 hrs)

### Recommended Before v1.0 (But Not Blockers)

- ⚠️ **Main Loop Tests** — RECOMMENDED (2-3 hrs)
- ⚠️ **Frontend Core Tests** — RECOMMENDED (6-8 hrs)

### Deferred to v1.1

- **Frontend Comprehensive Tests**
- **Integration Tests**
- **Runtime Config Edge Cases**
- **Alert Provider Error Paths**
- **Config Module SystemExit Test**

---

## Approval Status

**Current Coverage:** 91.36% (exceeds 90% requirement) ✅  
**Critical Gaps:** 2 high-priority items (ResourceWarnings + alert_provider_factory)  
**Recommendation:** **FIX ResourceWarnings + Add alert_provider_factory tests before v1.0**

**Approval Conditions:**

1. ResourceWarnings resolved (15 min)
2. `alert_provider_factory.py` coverage ≥90% (~20 tests, 3-4 hrs)
3. Re-run full test suite with no warnings

**Post-Fix Coverage Target:** 92-93%

---

**Review Completed By:** GitHub Copilot  
**Approval Status:** CONDITIONAL — Complete items 1-2 before v1.0 release  
**Next Steps:** Implement required tests, re-run coverage, update this document with final metrics
