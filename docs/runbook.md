---
layout: default
title: "Runbook"
description: "Operational guide for diagnosing and resolving production issues using logs and metrics."
---

Operational guide for diagnosing and resolving production issues using logs and metrics.

## Table of Contents

- [Log Interpretation](#log-interpretation)
- [Metric Thresholds](#metric-thresholds)
- [Alert Investigation](#alert-investigation)
- [SQLite Health](#sqlite-health)
- [Common Failure Scenarios](#common-failure-scenarios)
- [Escalation](#escalation)

---

## Log Interpretation

Hermes uses structured log lines at `INFO`, `WARNING`, and `ERROR` levels.

### Key Log Patterns

| Pattern | Level | Meaning |
|---|---|---|
| `Speedtest complete: X.X / X.X Mbps, X.X ms` | INFO | Normal run completed |
| `Speedtest failed` | ERROR | Runner could not complete test |
| `Exporter 'X' could not be initialized` | WARNING | Exporter skipped this cycle |
| `Alert sent successfully via X` | INFO | Alert provider delivered |
| `Alert provider 'X' failed` | ERROR | Provider could not send alert |
| `Runtime config saved` | INFO | UI-driven config change persisted |
| `PRAGMA wal_checkpoint` | DEBUG | SQLite WAL checkpoint triggered |
| `Running VACUUM` | INFO | SQLite fragmentation above 20 % |
| `pool_pending_approx=N` | INFO | Approximate in-flight alert tasks |

### Log Levels Summary

- **INFO**: Normal operational events; no action required.
- **WARNING**: Degraded operation (e.g., exporter skipped, retry attempted). Monitor for recurrence.
- **ERROR**: Failed operation; investigate root cause. App continues running.
- **CRITICAL**: Startup failures (e.g., missing required config). App may not function.

---

## Metric Thresholds

Prometheus metrics are exposed on `PROMETHEUS_PORT` (default `8000`). Suggested alert thresholds:

| Metric | Label | Warning | Critical |
|---|---|---|---|
| `hermes_download_mbps` | `server` | < 50 % of baseline | < 20 % of baseline |
| `hermes_upload_mbps` | `server` | < 50 % of baseline | < 20 % of baseline |
| `hermes_ping_ms` | `server` | > 2× baseline | > 5× baseline |
| `hermes_consecutive_failures_total` | — | ≥ 3 | ≥ failure\_threshold |

> **Tip:** Set `PROMETHEUS_DISABLE_LABELS=true` to reduce label cardinality if using a high-cardinality server pool.

---

## Alert Investigation

When an alert fires (`consecutive_failures >= failure_threshold`):

1. **Check recent logs** for `Speedtest failed` entries:

   ```text
   grep -i "speedtest failed" /var/log/hermes/app.log | tail -20
   ```

2. **Verify network connectivity** from the host running Hermes.

3. **Check speedtest-cli** is accessible and not rate-limited:

   ```bash
   speedtest-cli --simple
   ```

4. **Confirm alert provider config** via `GET /api/alerts/config` — ensure `enabled: true`
   and all provider URLs/tokens are set.

5. **Trigger a manual test** to rule out transient failure:

   ```bash
   curl -X POST http://localhost:8080/api/trigger -H "X-Api-Key: <key>"
   ```

6. **Check health endpoint**:

   ```bash
   curl http://localhost:8080/healthz
   ```

---

## SQLite Health

The SQLite database at `data/hermes.db` uses WAL mode. The exporter automatically:

- Runs `PRAGMA wal_checkpoint(TRUNCATE)` after any pruning cycle.
- Runs `VACUUM` when fragmentation exceeds 20 % (`freelist_count / page_count > 0.20`).

### Manual Health Check

```sql
sqlite3 data/hermes.db "PRAGMA integrity_check;"
sqlite3 data/hermes.db "PRAGMA page_count; PRAGMA freelist_count;"
```

### Signs of Problems

| Symptom | Likely Cause | Action |
|---|---|---|
| `database disk image is malformed` | Corruption | Restore from backup; re-initialise |
| WAL file growing indefinitely | Checkpoint blocked by long reader | Restart Hermes |
| Very slow queries | High fragmentation | Run `VACUUM` manually |

---

## Common Failure Scenarios

### Hermes fails to start

- Check `SPEEDTEST_INTERVAL_MINUTES` is a valid integer (≥ 1).
- Verify `PROMETHEUS_PORT` is not already in use.
- Confirm `.env` or environment variables are loaded.

### No results being written

- Ensure at least one exporter is listed in `ENABLED_EXPORTERS`.
- Confirm `data/` directory exists and is writable.
- Check for `Exporter 'X' could not be initialized` warnings in logs.

### Alerts not firing

- Confirm `ALERT_ENABLED=true`.
- Verify `ALERT_FAILURE_THRESHOLD` is set to expected value (default 3).
- Test delivery: `POST /api/alerts/test`.
- Check `pool_pending_approx` in logs — if always 0, thread pool may be exhausted.

### High Prometheus label cardinality

- Set `PROMETHEUS_DISABLE_LABELS=true` to collapse all label values to empty strings.
- This reduces each metric to a single time series regardless of server.

### Loki exporter silently skipped

- `LOKI_URL` must be set when `loki` is in `ENABLED_EXPORTERS`.
- Without it, the Loki factory returns `None` and the exporter is skipped with a WARNING.

---

## Escalation

If an issue cannot be resolved via the steps above:

1. Collect logs from the past 24 hours.
2. Export current Prometheus metrics snapshot.
3. Note the current runtime config (`GET /api/config`).
4. File an issue in the project repository with the above artefacts.

See also: [Error Catalog](error-catalog.md) | [Security Audit](SECURITY-AUDIT.md)
