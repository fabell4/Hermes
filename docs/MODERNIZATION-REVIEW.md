# Modernization & Deprecation Review

**Project:** Hermes Speed Monitor  
**Review Date:** 2026-04-30  
**Python Version:** 3.13  
**Scope:** Review for deprecated Python features and modernization opportunities  
**Prerequisites:** Security Audit ✅ | Defensive Coding Review ✅ | Best Practices Review ✅

---

## Executive Summary

This review scans the codebase for deprecated Python features, outdated patterns, and opportunities to leverage modern Python capabilities (3.10+). The codebase is already quite modern, having recently undergone type hint standardization and best practices improvements. The issues identified focus on consistency (context managers, configuration), type safety (enums), and technical debt cleanup.

**Overall Assessment:** ✅ **Approved for v1.0** with recommended improvements

**Key Findings:**

- ✅ No deprecated Python features or Python 2 artifacts found
- ✅ Already using modern type hints (`|` syntax, `list[T]`, `dict[K, V]`)
- ✅ Already using `datetime.now(timezone.utc)` (not deprecated `utcnow()`)
- ✅ Already using `pathlib.Path` extensively
- ✅ Proper context managers for most file operations
- 🔧 6 modernization opportunities identified (2 high, 3 medium, 1 low priority)

**Recommendation:** Implement high and medium priority improvements before v1.0 release. Low priority item is optional.

---

## Priority Levels

- 🔴 **HIGH** — Modern Python patterns that improve safety, reliability, or consistency
- 🟡 **MEDIUM** — Worthwhile improvements that reduce technical debt or enforce architecture
- 🟢 **LOW** — Optional stylistic improvements with minimal impact

---

## Issues Identified

### 🔴 HIGH Priority

#### Issue #1: SQLite Connections Not Using Context Managers

**Files:** [src/api/routes/results.py](../src/api/routes/results.py) (lines 62-76, 81-94)  
**Severity:** High — Inconsistent resource management pattern

**Problem:**
API route handlers for results pagination use manual `try/finally` blocks for SQLite connection cleanup:

```python
conn = _connect()
try:
    total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    # ... more operations
finally:
    conn.close()
```

**Impact:**

- Inconsistent with Python best practices (context managers preferred)
- More verbose than necessary
- While functionally correct, violates "prefer context managers for resource management" pattern

**Recommendation:**
Modify to use context manager protocol:

```python
with _connect() as conn:
    total: int = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    # ... more operations
```

**Implementation Note:** The `_connect()` function returns `sqlite3.Connection`, which already supports context manager protocol. Can use directly.

**Estimated Effort:** 15 minutes  
**Breaking Changes:** None (internal implementation only)

---

#### Issue #2: String Constants Should Be Enums

**File:** [src/constants.py](../src/constants.py)  
**Severity:** High — Missed opportunity for type safety

**Problem:**
Exporter and alert provider names are defined as string constants:

```python
# Exporter names
EXPORTER_CSV = "csv"
EXPORTER_PROMETHEUS = "prometheus"
EXPORTER_LOKI = "loki"
EXPORTER_SQLITE = "sqlite"

# Alert provider names
PROVIDER_WEBHOOK = "webhook"
PROVIDER_GOTIFY = "gotify"
PROVIDER_NTFY = "ntfy"
PROVIDER_APPRISE = "apprise"
```

**Impact:**

- No type safety — can pass arbitrary strings where exporter/provider names expected
- No IDE autocomplete support
- Risk of typos ("prometeus" vs "prometheus")
- Less clear intent

**Recommendation:**
Convert to `StrEnum` (Python 3.11+, available in 3.13):

```python
from enum import StrEnum

class ExporterType(StrEnum):
    """Valid exporter type identifiers."""
    CSV = "csv"
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    SQLITE = "sqlite"

class AlertProviderType(StrEnum):
    """Valid alert provider type identifiers."""
    WEBHOOK = "webhook"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    APPRISE = "apprise"
```

**Benefits:**

- Type safety: `def export(exporter: ExporterType)` vs `def export(exporter: str)`
- `StrEnum` inherits from `str`, so direct string comparisons still work: `if name == ExporterType.CSV`
- IDE autocomplete and refactoring support
- Self-documenting: all valid values visible in enum definition

**Migration Impact:**

- Need to update imports across codebase
- Can maintain backward compatibility by keeping `EXPORTER_*` as aliases during transition
- Type checkers will catch any invalid usage

**Estimated Effort:** 1 hour  
**Breaking Changes:** None if using aliases; minor if switching all references to enum

---

### 🟡 MEDIUM Priority

#### Issue #3: Environment Variable Access Outside Config Module

**File:** [src/services/speedtest_runner.py](../src/services/speedtest_runner.py) (line 75)  
**Severity:** Medium — Architecture principle violation

**Problem:**
The [config.py](../src/config.py) module explicitly documents:
> "Nowhere else in the app calls os.getenv() directly; everything imports from here."

However, `speedtest_runner.py` violates this:

```python
_tz_name = os.getenv("TZ", "UTC")
```

**Impact:**

- Inconsistent configuration pattern
- Makes testing harder (can't easily mock all config in one place)
- Violates stated architecture principle
- Duplicate default values across modules

**Recommendation:**
Add to [config.py](../src/config.py):

```python
# Timezone
TIMEZONE: str = os.getenv("TZ", "UTC")
```

Update [speedtest_runner.py](../src/services/speedtest_runner.py):

```python
from src import config
# ...
_tz_name = config.TIMEZONE
```

**Estimated Effort:** 5 minutes  
**Breaking Changes:** None (environment variable name unchanged)

---

#### Issue #4: Dead Log Service Code

**File:** [src/services/log_service.py](../src/services/log_service.py)  
**Severity:** Medium — Technical debt

**Problem:**
The entire `Log` class is a placeholder with no functionality:

```python
class Log:
    """Placeholder logging service kept for compatibility with earlier imports."""

    def __init__(self) -> None:
        self.enabled = True
```

**Impact:**

- Confuses new developers ("What does this do?")
- Increases maintenance burden (file must be maintained, type-checked, etc.)
- "Kept for compatibility" suggests unfinished migration

**Recommendation:**
Option A (Preferred): Remove the file entirely and fix any imports  
Option B: Add deprecation warning if removal is blocked:

```python
import warnings

class Log:
    """Deprecated: This class is no longer used and will be removed in v2.0."""

    def __init__(self) -> None:
        warnings.warn(
            "Log service is deprecated and will be removed in v2.0. "
            "Use standard logging module instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.enabled = True
```

**Action Required:**

1. Search codebase for `from src.services.log_service import Log`
2. If found, migrate to standard `logging` module
3. If not found, delete file

**Estimated Effort:** 15 minutes (verify no usage + delete) or 30 minutes (migration)  
**Breaking Changes:** None if file is truly unused

---

#### Issue #5: Lock Usage in Trigger Route Could Use Context Manager

**File:** [src/api/routes/trigger.py](../src/api/routes/trigger.py) (lines 66-79)  
**Severity:** Medium — Consistency improvement

**Problem:**
Background task manually releases lock in `finally` block:

```python
try:
    result = SpeedtestRunner().run()
    dispatcher.dispatch(result)
    # ... logging
except Exception as exc:
    logger.exception("Manual trigger failed: %s", exc)
finally:
    _test_lock.release()
```

Earlier in the function, the lock is acquired explicitly:

```python
if not _test_lock.acquire(blocking=False):
    raise HTTPException(status_code=409, detail="Test already running")
```

**Impact:**

- Less Pythonic than context manager
- Slightly more verbose
- Pattern inconsistency with rest of codebase

**Recommendation:**
Refactor to use context manager:

```python
if not _test_lock.acquire(blocking=False):
    raise HTTPException(status_code=409, detail="Test already running")

with _test_lock:
    result = SpeedtestRunner().run()
    dispatcher.dispatch(result)
    # ... logging
```

**Note:** This requires `_test_lock.acquire(blocking=False)` *before* the `with` statement to maintain the non-blocking check. The `with` statement should use `_test_lock` in "already acquired" mode. However, Python's `Lock` context manager will attempt to acquire again, so this pattern needs careful review.

**Alternative (Simpler):**
Keep current pattern as it's actually more correct for the non-blocking check. The issue is borderline — current implementation is valid.

**Estimated Effort:** 30 minutes (with testing to verify behavior)  
**Breaking Changes:** None

**Status:** **OPTIONAL** — Current pattern is actually appropriate given the non-blocking requirement. Context manager would require more complex refactoring.

---

### 🟢 LOW Priority

#### Issue #6: Dict Merge Could Use | Operator

**File:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py) (lines 57-63)  
**Severity:** Low — Stylistic preference

**Current:**

```python
labels: dict[str, str] = {
    "job": self._job_label,
    "server_name": result.server_name or "unknown",
    "server_location": result.server_location or "unknown",
}
labels.update(self._static_labels)
return labels
```

**Could be:**

```python
return {
    "job": self._job_label,
    "server_name": result.server_name or "unknown",
    "server_location": result.server_location or "unknown",
} | self._static_labels
```

**Assessment:**

- Python 3.9+ dict merge operator (`|`) is more functional/concise
- However, current pattern is clear, readable, and explicit
- This is purely stylistic with no functional benefit

**Recommendation:** **NO ACTION** — Current code is fine. The `update()` pattern is well-understood and equally modern.

---

## Summary

### Issues by Priority

| Priority | Count | Status |
|----------|-------|--------|
| 🔴 High | 2 | To implement |
| 🟡 Medium | 3 | To implement (1 optional) |
| 🟢 Low | 1 | No action |

### Deprecated Features Found

**None.** The codebase does not use any deprecated Python features:

- ✅ No `datetime.utcnow()` (uses `datetime.now(timezone.utc)`)
- ✅ No Python 2 artifacts (`unicode`, `basestring`, old exception syntax)
- ✅ No deprecated standard library functions
- ✅ Modern type hints throughout
- ✅ No `typing.Dict/List/Tuple` (uses `dict`/`list`/`tuple`)

### Already Modernized

- ✅ Type hints use modern `|` syntax (`str | None` instead of `Optional[str]`)
- ✅ Collections use lowercase (`list[str]` not `List[str]`)
- ✅ `from __future__ import annotations` where needed
- ✅ Dataclasses used (`SpeedResult`)
- ✅ Context managers for file I/O
- ✅ `pathlib.Path` preferred over `os.path`
- ✅ Logging uses `%` formatting (correct pattern for logging performance)

---

## Implementation Plan

### Phase 1: High Priority (Required for v1.0)

1. **SQLite Context Managers** (#1)
   - Update `src/api/routes/results.py`
   - Convert `try/finally` to `with` statements
   - Test pagination endpoints

2. **String to Enum Conversion** (#2)
   - Add `ExporterType` and `AlertProviderType` enums to `constants.py`
   - Update all references across codebase
   - Verify type checking passes
   - Run full test suite

### Phase 2: Medium Priority (Recommended for v1.0)

1. **Centralize TZ Config** (#3)
   - Add `TIMEZONE` to `config.py`
   - Update `speedtest_runner.py` to import from config
   - Verify no behavior changes

2. **Clean Up Dead Code** (#4)
   - Search for `log_service` imports
   - Remove file if unused or add deprecation warning
   - Update any references

3. **Review Lock Context Manager** (#5)
   - Analyze non-blocking lock semantics
   - Decide if refactoring improves clarity
   - Keep current pattern if it's most correct

### Phase 3: Validation

1. **Testing**
   - Run `pytest` with coverage (must remain >90%)
   - Run `mypy` (must pass)
   - Run `ruff check` (must pass)
   - Manual smoke test of API endpoints

2. **Documentation**
   - Update this document with implementation results
   - Mark TODO.md item as complete
   - Update CHANGELOG.md

---

## Test Coverage Impact

**Expected:** All changes are refactoring/modernization with identical behavior. Test coverage should remain stable (~95%). No new test cases required unless behavior changes.

**Validation:**

```bash
pytest --cov=src --cov-report=html --cov-report=term
# Must show ≥90% coverage
```

---

## Approval Status

- [x] High priority fixes implemented
- [x] Medium priority fixes implemented (lock usage marked as optional - current pattern is correct)
- [x] All tests passing (344 tests)
- [x] Static analysis clean (mypy, ruff)
- [x] Code coverage ≥90% (91.36%)
- [x] Ready for v1.0 release

---

## Implementation Results

**Date Completed:** 2026-04-30

### Changes Implemented

#### ✅ Issue #1: SQLite Connections Context Managers

**Status:** COMPLETE  
**Files Modified:** [src/api/routes/results.py](../src/api/routes/results.py)

Converted both `get_results()` and `get_latest_result()` to use context managers:

```python
with _connect() as conn:
    # database operations
```

**Result:** Code is now more concise and consistent with Python best practices.

---

#### ✅ Issue #2: String Constants to Enums

**Status:** COMPLETE  
**Files Modified:** [src/constants.py](../src/constants.py), [src/main.py](../src/main.py)

Added `ExporterType` and `AlertProviderType` as `StrEnum` classes:

```python
class ExporterType(StrEnum):
    CSV = "csv"
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    SQLITE = "sqlite"

class AlertProviderType(StrEnum):
    WEBHOOK = "webhook"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    APPRISE = "apprise"
```

Maintained backward compatibility by keeping old constant names as aliases. Updated type annotations in `main.py` to use `dict[str, Callable[[], BaseExporter]]` for runtime flexibility while maintaining type safety.

**Result:** Type safety improved with IDE autocomplete support, while maintaining full backward compatibility.

---

#### ✅ Issue #3: Centralized TZ Environment Variable

**Status:** COMPLETE  
**Files Modified:** [src/config.py](../src/config.py), [src/services/speedtest_runner.py](../src/services/speedtest_runner.py)

Added `TIMEZONE` constant to `config.py`:

```python
TIMEZONE: str = os.getenv("TZ", "UTC")
```

Updated `speedtest_runner.py` to import from config instead of calling `os.getenv()` directly.

**Result:** All configuration now centralized in `config.py`, enforcing architecture principle.

---

#### ✅ Issue #4: Removed Dead Log Service Code

**Status:** COMPLETE  
**Files Deleted:** `src/services/log_service.py`

Verified no imports existed and removed the unused placeholder class.

**Result:** Reduced technical debt, removed confusing dead code.

---

#### ⚪ Issue #5: Lock Usage in trigger.py

**Status:** NO ACTION (OPTIONAL)  
**Rationale:** Current pattern is correct for the non-blocking lock acquisition across thread boundaries. Lock is acquired in `trigger_test()` and released in `_run_test()` running in a background thread. Context manager refactoring would be more complex without benefits.

**Result:** Keeping existing implementation as it is appropriate for the use case.

---

### Test Results

**All 344 tests passing:**

- Unit tests: ✅
- Integration tests: ✅
- API tests: ✅  
- Coverage: **91.36%** (target: ≥90%)

**Static Analysis:**

- mypy: ✅ No errors (26 files checked)
- ruff: ✅ All checks passed

---

## Notes

This review represents the fourth and final planned code quality review before v1.0 release. Combined with the Security Audit, Defensive Coding Review, and Best Practices Review, the codebase has undergone comprehensive scrutiny. The issues identified are minor modernization opportunities rather than fundamental problems.

Post-v1.0 quality improvements can be tracked in the "Post-Release Enhancements" section of TODO.md.
