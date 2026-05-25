---
description: "Use when performing any code review, security audit, pre-release quality check, or dependency vulnerability review. Covers all nine review categories, their acceptance criteria, exit gates, and finding classification rules."
---

# Code Review Policy

<!-- ─────────────────────────────────────────────────────────────────────────
     SHARED TEMPLATE — Sections 1–11 are identical across Argus and Hermes.
     Section 12 is project-specific to this repository.
     When editing shared sections, apply the same change to the other project.
     ───────────────────────────────────────────────────────────────────────── -->

## Review Sequencing

Perform reviews in this order. Each category is a prerequisite for the next.
Do not mark a category complete while it has any open HIGH findings.

1. Supply Chain Security
2. Application Security Audit
3. Defensive Coding Review
4. Best Practices Review
5. Modernization Review
6. Error Handling Review
7. Test Coverage Review
8. Documentation Accuracy Review
9. Performance Review

---

## Severity Levels

| Level | Symbol | Release Impact |
|-------|--------|----------------|
| HIGH | 🔴 | Blocks release. Must be resolved and verified before any release tag. |
| MEDIUM | 🟡 | Should be resolved before release. May be deferred to next minor with a tracked TODO entry. |
| LOW | 🟢 | Deferred to post-release backlog is acceptable. |

---

## Category 1: Supply Chain Security

**This category must pass before any other review begins.**

Supply chain scanning must be the first gate, not a downstream CI artifact. Application-level
security controls are meaningless if a dependency ships a known remote code execution or SSRF
vulnerability. CVEs are published continuously after packages are pinned; automated scanning
catches what manual audits cannot.

### Checklist

- [ ] `pip-audit -r requirements.txt` exits 0 with zero known vulnerabilities
- [ ] `npm audit --omit=dev` (from `frontend/`) exits 0 with no high or critical findings
- [ ] No pinned package version has an open CVE at MEDIUM severity or above
- [ ] Dependency update automation is enabled and configured for pip, npm, and Actions

### Pass Criteria

All scan commands exit 0. Any CVE rated HIGH or CRITICAL blocks release unconditionally —
this overrides any other severity classification. Document each finding: CVE ID, affected
package, fix version, resolving commit.

---

## Category 2: Application Security Audit

### Authentication & Authorisation

- [ ] API key comparison uses `secrets.compare_digest()` (timing-safe)
- [ ] Missing key returns HTTP 401; invalid key returns HTTP 403
- [ ] All state-mutating endpoints (`POST`, `PUT`, `DELETE`) require authentication
- [ ] Public read-only endpoints are explicitly enumerated and each has a justification
- [ ] Minimum API key length enforced at startup (≥32 characters)

### Rate Limiting

- [ ] Rate-limiting middleware applied to all API routes
- [ ] Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`) present
- [ ] Rate limit values are configurable via environment variable

### Input Validation

- [ ] All request bodies validated through Pydantic models (no raw `dict` parsing)
- [ ] Path and query parameters have explicit type annotations and constraints
- [ ] No user-supplied data concatenated into SQL — parameterised queries only

### SSRF Prevention

- [ ] All operator- or user-supplied URLs validated before first use
- [ ] Scheme restricted to `https://`; `http://`, `file://`, and `data:` are rejected with a
      clear error message
- [ ] URL validation occurs at configuration/storage time, not at call time

### Security Headers & CORS

- [ ] `X-Content-Type-Options: nosniff` present on all API responses
- [ ] `X-Frame-Options: DENY` present
- [ ] CORS allowed-origin list is explicit — wildcard `*` is not used in production configuration
- [ ] Secrets never logged, even partial (no `key[:8]` style partial logging)

---

## Category 3: Defensive Coding Review

- [ ] All env var helpers (`_get_int`, `_get_float`, etc.) validate range, not just type —
      negative values and zero rejected where invalid
- [ ] All persistent state writes use atomic pattern: write to temp file → `os.replace()` into
      final path
- [ ] All SQLite connections opened with a `timeout` parameter
- [ ] All SQLite connections use context manager protocol (`with conn:`)
- [ ] All file handles use `with` blocks — no manual `.close()`
- [ ] Shared mutable state accessed from multiple threads protected by `threading.Lock`
- [ ] All outbound HTTP calls specify explicit connect and read timeouts
- [ ] Background thread / scheduler exceptions caught at thread boundary, logged with traceback,
      and do not silently terminate the thread

---

## Category 4: Best Practices Review

- [ ] No magic strings — all repeated string values extracted to `StrEnum` or module constants
- [ ] No business logic duplicated across more than one module
- [ ] All public functions and class methods have complete type annotations
- [ ] Type annotations use Python 3.10+ union syntax: `X | Y` (not `Optional[X]` or `Union`)
- [ ] Imports organised: stdlib → third-party → local, one blank line between groups
- [ ] No bare `except:` clauses — always name the exception type
- [ ] No `except Exception: pass` silent swallows — always log or re-raise
- [ ] No `# type: ignore` without a trailing comment explaining the specific suppression

---

## Category 5: Modernization Review

- [ ] No `datetime.utcnow()` — use `datetime.now(timezone.utc)`
- [ ] No `os.path.*` for path construction — use `pathlib.Path`
- [ ] No `Optional[X]` — use `X | None`
- [ ] No `Union[X, Y]` — use `X | Y`
- [ ] No `Dict[K, V]`, `List[T]`, `Tuple[...]` from `typing` — use lowercase builtins
- [ ] String enum constants use `StrEnum` (Python 3.11+)
- [ ] No deprecated `typing.io` or `typing.re` imports (removed in 3.12)
- [ ] SQLite `Connection` objects used as context managers, not manually `.close()`'d

---

## Category 6: Error Handling Review

- [ ] Every `except` block either logs at WARNING or higher, or re-raises — no silent catches
- [ ] HTTP error responses return structured JSON (`{"detail": "..."}`) — not raw exception text
- [ ] All network calls have explicit `timeout` parameters (connect + read)
- [ ] Startup failures (missing required config, unreachable services) log a clear message and
      exit with non-zero code
- [ ] Background/scheduler exceptions caught at thread boundary and logged with full traceback
- [ ] All custom exception classes are project-defined (no bare `raise "string"`)
- [ ] Error catalog updated for any new error codes or messages introduced in this cycle

---

## Category 7: Test Coverage Review

- [ ] `pytest --cov=src --cov-fail-under=90` exits 0 (Python backend ≥90%)
- [ ] `vitest run --coverage` (from `frontend/`) shows ≥70% statement coverage
- [ ] `pytest -W error::ResourceWarning` exits 0 — zero unclosed connections or file handles
- [ ] Every new source module introduced has at least one corresponding test file
- [ ] No `pytest.mark.skip` without `reason=` argument and a tracking issue reference
- [ ] At least one integration test covers each major data path (poll → store, event → alert)

---

## Category 8: Documentation Accuracy Review

- [ ] All `README.md` setup commands tested on a clean checkout and produce the documented result
- [ ] `README.md` test count and coverage percentage match the most recent CI run
- [ ] Every environment variable in `config.py` is present in `.env.example` with a description
- [ ] Every env var documented in README is also in `.env.example`
- [ ] API endpoint table in README matches actual FastAPI route definitions (path, method, auth)
- [ ] `CHANGELOG.md` has an entry for every user-visible change in this review cycle
- [ ] `CONTRIBUTING.md` setup steps work on a clean checkout (Windows and Linux)

---

## Category 9: Performance Review

- [ ] All database tables queried with date ranges have a timestamp index
- [ ] No blocking I/O (database, file, network) on the FastAPI async request path
- [ ] Runtime configuration cached with mtime check — not re-read from disk on every request
- [ ] Alert providers use HTTP connection pooling (a persistent `requests.Session`)
- [ ] Prometheus metric labels use only bounded, finite value sets — no per-request dynamic labels
- [ ] SQLite connections not opened and closed on every request in hot query paths

---

## Exit Criteria

A release tag **MUST NOT** be cut until every row in this table is green.

| Gate | Verification |
|------|--------------|
| Supply chain — pip | `pip-audit -r requirements.txt` exits 0 |
| Supply chain — npm | `npm audit --omit=dev` exits 0 (no high/critical) |
| Tests pass | `pytest` exits 0 |
| Python coverage ≥90% | `pytest --cov=src --cov-fail-under=90` exits 0 |
| Frontend coverage ≥70% | `vitest run --coverage` from `frontend/` ≥70% statements |
| No ResourceWarnings | `pytest -W error::ResourceWarning` exits 0 |
| Ruff lint clean | `ruff check src` exits 0 |
| Ruff format clean | `ruff format --check src` exits 0 |
| Mypy | `mypy src` exits 0; all `# type: ignore` lines have explanatory comments |
| No open HIGH findings | All 🔴 HIGH items across all 9 categories resolved and committed |
| Docs current | README test count and API table verified against current codebase |

---

## Finding Classification

Record each finding with this structure:

```
ID:             {CATEGORY}-{N}   e.g. SC-1, SEC-3, DEF-2, PERF-1
File:           src/path/to/file.py  line N
Severity:       HIGH | MEDIUM | LOW
Summary:        one-line description
Detail:         what is wrong and why it matters
Recommendation: specific change required
Resolution:     commit SHA or "deferred to vX.Y — see TODO.md"
```

Category abbreviations:

| Abbrev | Category |
|--------|----------|
| `SC` | Supply Chain Security |
| `SEC` | Application Security Audit |
| `DEF` | Defensive Coding |
| `BP` | Best Practices |
| `MOD` | Modernization |
| `ERR` | Error Handling |
| `COV` | Test Coverage |
| `DOC` | Documentation Accuracy |
| `PERF` | Performance |

---

## Project-Specific Configuration — Hermes

**Runtime:** Python 3.13+, Node.js 22+
**Architecture:** Single-process — scheduler and API run in the same process
**Frontend:** React 18 / TypeScript / Vite / Vitest
**Dependency automation:** Renovate (pip, npm, GitHub Actions)

### Additional Supply Chain Steps

- Run `npm audit --omit=dev` from the `frontend/` subdirectory, not the project root
- Renovate PRs for patch-level dependency bumps may be merged without a release tag per the
  release policy; confirm the updated dependency passes `pip-audit` before merging

### Additional Security Checks

- All alert provider URLs (Webhook, Gotify, ntfy, Apprise) must be validated for `https://`
  scheme before being written to `data/runtime_config.json`
- The speedtest binary path is not user-configurable; document and enforce this restriction to
  prevent command injection via config

### Coverage Thresholds

| Layer | Command | Gate |
|-------|---------|------|
| Python | `pytest --cov=src --cov-fail-under=90` | ≥90% |
| Frontend | `vitest run --coverage` from `frontend/` | ≥70% statements |
