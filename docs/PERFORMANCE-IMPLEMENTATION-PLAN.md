# Performance Optimization Implementation Plan

**Review:** [PERFORMANCE-OPTIMIZATION-REVIEW.md](PERFORMANCE-OPTIMIZATION-REVIEW.md)  
**Status:** Ready for implementation  
**Estimated Total Effort:** 4-5 hours  
**Target:** v1.0 release

---

## High Priority Items (Required for v1.0)

### ✅ Issue #1: SQLite Timestamp Index

**Status:** Not started  
**Estimated Effort:** 1 hour  
**Priority:** Critical — Affects API query performance

**Changes Required:**

1. Update `_CREATE_TABLE` in [src/exporters/sqlite_exporter.py](../src/exporters/sqlite_exporter.py) to include index creation
2. Add index migration to `_MIGRATIONS` list
3. Update `_init_db()` to check for missing indexes (not just columns)
4. Add tests to verify index exists and is used

**Files to modify:**

- `src/exporters/sqlite_exporter.py` (lines 39-48, 107-127)

**Test coverage:**

- [ ] Test index creation on new database
- [ ] Test index migration on existing database
- [ ] Test query performance with index vs without
- [ ] Test pruning performance with index

**Performance Impact:** 10-100× faster queries for tables with >1,000 rows

---

### ✅ Issue #2: Async Alert Sending

**Status:** Not started  
**Estimated Effort:** 2-3 hours  
**Priority:** High — Prevents scheduler blocking

**Changes Required:**

1. Add `concurrent.futures.ThreadPoolExecutor` to `AlertManager.__init__()`
2. Create `_send_alert_async()` helper method
3. Update `_maybe_send_alert()` to submit alerts to thread pool
4. Keep `send_test_alert()` synchronous (for API response)
5. Add tests for async behavior

**Files to modify:**

- `src/services/alert_manager.py` (lines 138-147, 176-207)

**Test coverage:**

- [ ] Test alerts are sent without blocking
- [ ] Test multiple providers execute in parallel
- [ ] Test alert failure doesn't crash thread
- [ ] Test `send_test_alert()` remains synchronous
- [ ] Test thread pool cleanup on shutdown

**Performance Impact:** Alert sending overhead reduced from 30s worst case to <1ms (non-blocking)

---

### ✅ Issue #3: Static File Middleware

**Status:** Not started  
**Estimated Effort:** 1 hour  
**Priority:** High — Improves page load time

**Changes Required:**

1. Mount static files BEFORE adding middleware
2. Verify middleware still applies to API routes
3. Test that static files bypass middleware
4. Update comments documenting the order

**Files to modify:**

- `src/api/main.py` (lines 115-127, 173-182)

**Test coverage:**

- [ ] Test API routes still have middleware (rate limiting, headers)
- [ ] Test static files bypass middleware
- [ ] Test CORS still works for API
- [ ] Test security headers on API responses
- [ ] Integration test: full page load

**Performance Impact:** 100-200 µs per static asset request (20% faster page loads)

---

## Medium Priority Items (Monitor, then implement in v1.1)

### 🟡 Issue #4: Prometheus Label Cardinality

**Status:** Deferred to v1.1  
**Action:** Monitor Prometheus memory usage and time series count

**Monitoring Command:**

```bash
# Check number of hermes time series
curl http://localhost:9090/api/v1/label/__name__/values | grep hermes | wc -l

# Check memory usage
docker stats prometheus
```

**Trigger for implementation:** >1,000 unique time series OR >100MB memory growth

---

### 🟡 Issue #5: Exporter Registry Duplication

**Status:** Deferred to v1.1  
**Effort:** 30 minutes  
**Priority:** Code quality improvement

---

### 🟡 Issue #6: SQLite WAL Checkpoint

**Status:** Deferred to v1.1  
**Effort:** 30 minutes  
**Priority:** Reduces disk usage

**Monitoring Command:**

```bash
# Check WAL file size
ls -lh data/hermes.db*
```

**Trigger for implementation:** WAL file >10MB OR user complaints about disk usage

---

### 🟡 Issue #7: HTTP Connection Pooling

**Status:** Deferred to v1.1  
**Effort:** 2 hours  
**Priority:** Only beneficial if testing interval <5 minutes

---

## Implementation Checklist

- [ ] **Issue #1: SQLite Timestamp Index**
  - [ ] Update schema with index
  - [ ] Add migration logic
  - [ ] Write tests
  - [ ] Verify performance improvement
  - [ ] Document change in CHANGELOG

- [ ] **Issue #2: Async Alert Sending**
  - [ ] Add ThreadPoolExecutor
  - [ ] Implement async sending
  - [ ] Update tests
  - [ ] Verify non-blocking behavior
  - [ ] Document change in CHANGELOG

- [ ] **Issue #3: Static File Middleware**
  - [ ] Reorder middleware and mounts
  - [ ] Update tests
  - [ ] Verify API middleware still works
  - [ ] Document change in CHANGELOG

- [ ] **Validation**
  - [ ] All 397 tests passing
  - [ ] No static analysis errors (mypy, ruff)
  - [ ] Code coverage maintained (≥90%)
  - [ ] Manual testing of API performance
  - [ ] Manual testing of page load speed

- [ ] **Documentation**
  - [ ] Update CHANGELOG.md
  - [ ] Update README if needed
  - [ ] Update TODO.md

---

## Regression Testing Commands

After implementing optimizations, run full test suite:

```bash
# Python tests
pytest tests/ -v --cov=src --cov-report=term-missing

# Static analysis
mypy src/
ruff check src/

# API integration tests
pytest tests/api/ -v

# Frontend tests
cd frontend && npm test

# Manual performance test
python -m pytest tests/performance/ -v --benchmark
```

---

## Performance Benchmarks (Before/After)

Record benchmarks before and after implementation:

| Operation | Before (ms) | After (ms) | Improvement |
|-----------|-------------|------------|-------------|
| SQLite query (10 rows, 10K total) | 50-100 | _TBD_ | _TBD_ |
| SQLite pruning (10K rows) | 200-500 | _TBD_ | _TBD_ |
| API `/results` response | 60-120 | _TBD_ | _TBD_ |
| Alert sending (3 providers) | 150-30000 | _TBD_ | _TBD_ |
| Static asset serving | 1-2 | _TBD_ | _TBD_ |

---

## Approval Criteria

✅ **Ready for v1.0 when:**

1. All 3 high priority issues implemented
2. All tests passing (397+ tests)
3. Code coverage ≥90%
4. Static analysis clean
5. Performance benchmarks show expected improvements
6. No new bugs introduced
7. Documentation updated

---

**Next Steps:**

1. Start with Issue #1 (SQLite index) — highest impact, easiest to implement
2. Proceed to Issue #2 (async alerts) — most complex, needs careful testing
3. Finish with Issue #3 (middleware) — simple but needs integration testing
4. Run full validation suite
5. Update documentation
6. Ready for v1.0 release! 🎉
