---
layout: default
title: "Error Catalog"
---

# Error Catalog

**Project:** Hermes Speed Monitor  
**Last Updated:** 2026-05-01  
**Purpose:** Comprehensive list of all possible errors by module with causes and remediation

---

## Table of Contents

- [API Module](#api-module)
- [Configuration Module](#configuration-module)
- [Dispatcher Module](#dispatcher-module)
- [Exporters](#exporters)
- [Services](#services)
- [Error Matrix](#error-matrix)

---

## API Module

### Authentication & Authorization (`src/api/auth.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Missing X-Api-Key header | `HTTPException(401)` | High | Client didn't send required header | Add `X-Api-Key` header to all requests |
| Invalid API key | `HTTPException(403)` | High | API key doesn't match configured value | Verify API key matches `.env` configuration |
| Rate limit exceeded | `HTTPException(429)` | Medium | Too many requests from client | Implement backoff, reduce request frequency |

**Prevention:**
- Always send `X-Api-Key` header
- Store API key securely (environment variable, secrets vault)
- Implement client-side rate limiting

---

### Configuration Routes (`src/api/routes/config.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Invalid configuration payload | `HTTPException(400)` | Medium | Validation failed on config update | Check interval (5-1440), valid exporter names |
| Runtime config save failed | `HTTPException(500)` | High | Filesystem error saving config | Check permissions, disk space |

**Prevention:**
- Validate payload before sending (client-side validation)
- Ensure data directory is writable
- Use atomic writes (handled by backend)

---

### Results Routes (`src/api/routes/results.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| No database found yet | `HTTPException(503)` | Low | No speedtests have run | Wait for first test or trigger manually |
| Invalid pagination parameters | `HTTPException(400)` | Low | page/page_size out of range | Use page ≥ 1, page_size 1-500 |
| Database query failed | `HTTPException(500)` | High | SQLite error during query | Check database integrity, reduce page_size |

**Prevention:**
- Enable SQLite exporter
- Trigger first speedtest after deployment
- Use reasonable page sizes (≤100)

---

### Trigger Routes (`src/api/routes/trigger.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Failed to start manual test thread | `HTTPException(500)` | High | Thread creation failed | Check system resources, restart container |
| Trigger file write failed | Internal | Medium | Filesystem error | Check permissions on data directory |

**Prevention:**
- Monitor system resources (threads, memory)
- Ensure data directory is writable
- Don't trigger tests too frequently (respect rate limits)

---

### Alert Routes (`src/api/routes/alerts.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Threshold must be positive integer | `HTTPException(400)` | Low | Invalid alert threshold | Use threshold ≥ 1 |
| Cooldown must be positive integer | `HTTPException(400)` | Low | Invalid cooldown | Use cooldown ≥ 1 (minutes) |
| Webhook URL invalid scheme | `HTTPException(400)` | Medium | URL doesn't start with http/https | Use http:// or https:// |
| Gotify/ntfy URL required | `HTTPException(400)` | Medium | Provider enabled but URL missing | Provide valid URL for enabled provider |
| Gotify token required | `HTTPException(400)` | Medium | Token missing for Gotify | Provide app token from Gotify |
| ntfy topic required | `HTTPException(400)` | Medium | Topic missing for ntfy | Provide topic name for ntfy |
| SSRF protection triggered | `HTTPException(400)` | High | URL points to private IP | Use public URLs only (not 127.0.0.1, 10.x, etc.) |

**Prevention:**
- Validate alert configuration before submitting
- Use only public URLs for webhooks (no localhost, private IPs)
- Keep threshold reasonable (2-5 failures)
- Set cooldown to avoid alert storms (60+ minutes recommended)

---

## Configuration Module

### Environment Configuration (`src/config.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| API_KEY not set | `SystemExit(1)` | Critical | Missing required env var | Set `API_KEY` in `.env` file |
| API_KEY validation failed | `SystemExit(1)` | Critical | API key too short (<32 chars) | Generate secure key: `openssl rand -hex 32` |
| Invalid PROMETHEUS_PORT | `ValueError` | High | Port not integer or out of range | Use port 1-65535 |
| Invalid RATE_LIMIT | `ValueError` | Medium | Rate limit not positive integer | Use positive integer (recommended: 60) |
| Invalid LOKI_TIMEOUT | `ValueError` | Medium | Timeout not positive | Use positive integer (seconds) |

**Prevention:**
- Use `.env.example` as template
- Generate secure random API key
- Validate environment variables before deployment
- Use default ports when possible (Prometheus: 9090)

---

### Runtime Configuration (`src/runtime_config.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Runtime config file corrupted | Warning | Medium | Malformed JSON | Delete file, allow regeneration |
| interval_minutes out of range | Warning | Low | Value not 5-1440 | Fallback to default (60) |
| enabled_exporters not a list | Warning | Low | Wrong type | Fallback to default (all enabled) |
| Unknown exporter in list | Warning | Low | Invalid exporter name | Filtered out, valid ones kept |
| Alert threshold out of range | Warning | Low | Not 1-100 | Fallback to default (3) |
| Alert cooldown out of range | Warning | Low | Not 1-10080 | Fallback to default (60) |
| Could not save runtime config | `RuntimeError` | High | Filesystem error | Check permissions, disk space |
| Temp file cleanup failed | Warning | Low | Orphaned temp file | Non-fatal, temp file remains |

**Prevention:**
- Don't manually edit runtime_config.json (use API)
- Ensure data directory is writable
- Monitor disk space
- Regular backups of config file

---

## Dispatcher Module

### Result Dispatcher (`src/result_dispatcher.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Invalid result type | `TypeError` | Critical | Non-exporter passed to register() | Programming error - fix code |
| Exporter registration duplicate | Warning | Low | Same exporter registered twice | Ignored, last registration wins |
| No exporters registered | Warning | Medium | dispatch() called with no exporters | Enable at least one exporter |
| One or more exporters failed | `DispatchError` | Medium | Exporter threw exception | Check exporter-specific logs |
| All exporters failed | `DispatchError` | High | Every exporter failed | Check system health, connectivity |

**Prevention:**
- Always register at least one exporter
- Monitor exporter health (Prometheus, Loki, SQLite)
- Test exporters individually before enabling
- Check network connectivity for remote exporters

---

## Exporters

### CSV Exporter (`src/exporters/csv_exporter.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| CSV file write failed | `OSError` | High | Filesystem error | Check permissions, disk space |
| CSV directory creation failed | `OSError` | High | Parent directory not writable | Verify logs/ directory permissions |
| CSV pruning failed | Warning | Low | Error reading/writing for prune | Non-fatal, file continues to grow |
| CSV file corrupted | `ValueError` | Medium | Invalid CSV format | Backup and recreate file |
| Max rows exceeded (prune disabled) | Warning | Low | File growing unbounded | Enable pruning or manual cleanup |

**Prevention:**
- Ensure logs/ directory exists and is writable
- Enable pruning (max_rows or retention_days)
- Monitor file size: `du -h logs/results.csv`
- Regular backups of CSV file

---

### Prometheus Exporter (`src/exporters/prometheus_exporter.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Invalid port number | `ValueError` | Critical | Port not 1-65535 | Use valid port number |
| Port already in use | `RuntimeError` | Critical | Another process bound to port | Use different port or kill process |
| Failed to start HTTP server | `RuntimeError` | Critical | Server startup failed | Check network config, firewall |
| Failed to update gauges | Warning | Medium | Metric update error | Check result data validity |
| Label cardinality too high | Warning | Low | Too many unique label combinations | Disable dynamic labels if needed |

**Prevention:**
- Use dedicated port for Prometheus (9090-9100)
- Check port availability before starting: `netstat -an | grep :9090`
- Monitor metric cardinality (avoid unbounded ISP labels)
- Use `make labels optional` feature if cardinality is issue

---

### Loki Exporter (`src/exporters/loki_exporter.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Loki URL is required | `ValueError` | Critical | URL not configured | Set `LOKI_URL` environment variable |
| Loki URL invalid scheme | `ValueError` | Critical | URL not http/https | Use http:// or https:// |
| Loki URL missing hostname | `ValueError` | Critical | URL has no host | Provide full URL with hostname |
| Loki URL includes credentials | Warning | Medium | URL has username/password | Remove credentials, use auth headers |
| Timeout must be positive | `ValueError` | Medium | Invalid timeout value | Use positive integer (seconds) |
| Loki job label empty | `ValueError` | Medium | Job name is blank | Provide non-empty job name |
| Loki push connection error | `RuntimeError` | High | Network/DNS failure | Check connectivity, DNS, firewall |
| Loki push timed out | `RuntimeError` | High | Loki didn't respond in time | Increase timeout, check Loki health |
| Loki push rejected (HTTP error) | `RuntimeError` | High | Loki returned 4xx/5xx | Check Loki logs, verify auth/tenant |

**Prevention:**
- Test Loki connectivity before enabling: `curl http://loki:3100/ready`
- Use reasonable timeout (5-10 seconds)
- Monitor Loki health and resource usage
- Verify Loki authentication/tenant configuration
- Check network latency to Loki

---

### SQLite Exporter (`src/exporters/sqlite_exporter.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| SQLite write failed | `RuntimeError` | High | INSERT failed | Check disk space, permissions, schema |
| Database locked (timeout) | `SQLiteLockTimeout` | High | Lock held for >30s | Reduce page_size, check for long queries |
| Database initialization failed | `RuntimeError` | Critical | Schema creation failed | Check permissions, disk space |
| Database migration failed | `RuntimeError` | Critical | ALTER TABLE failed | Backup DB, review migration code |
| Database corrupted | `sqlite3.DatabaseError` | Critical | Integrity check failed | Restore from backup or recreate |
| Disk full during write | `OSError` | Critical | No space for database growth | Free disk space or increase volume size |

**Prevention:**
- Use WAL mode (enabled by default) for better concurrency
- Monitor database size: `du -h data/results.db`
- Regular integrity checks: `sqlite3 data/results.db "PRAGMA integrity_check;"`
- Keep page_size reasonable (≤100) for queries
- Monitor disk space usage
- Regular backups of database file

---

## Services

### Speedtest Runner (`src/services/speedtest_runner.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| speedtest-cli not found | `FileNotFoundError` | Critical | Command not installed | Install: `pip install speedtest-cli` |
| Speedtest execution failed | `RuntimeError` | High | Command returned non-zero | Check internet connectivity |
| Speedtest timed out (>120s) | `TimeoutError` | High | Test didn't complete in time | Check network speed, ISP issues |
| JSON parse failed | `ValueError` | High | Invalid JSON from speedtest | Update speedtest-cli, check stderr |
| Result validation failed | `ValueError` | Medium | Missing required fields | Update speedtest-cli version |
| All retry attempts exhausted | `RuntimeError` | High | Both attempts failed | Check persistent connectivity issues |

**Prevention:**
- Verify speedtest-cli is installed: `speedtest --version`
- Test manually: `speedtest --json`
- Check internet connectivity: `ping 8.8.8.8`
- Monitor consecutive failure count for alerts
- Verify ISP is not blocking speedtest traffic

---

### Alert Manager (`src/services/alert_manager.py`)

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Alert provider send failed | Warning | Medium | Provider threw exception | Check provider-specific logs |
| All alert providers failed | Warning | High | Every enabled provider failed | Check connectivity, provider health |
| Thread pool exhausted | Warning | High | Too many pending alerts | Increase thread pool size |
| Alert send timed out | Warning | Medium | Provider didn't respond | Check provider health, network |

**Prevention:**
- Test alert providers before enabling
- Monitor alert provider health
- Don't set threshold too low (avoid alert storms)
- Use cooldown to rate-limit alerts (60+ minutes)
- Verify network connectivity to alert services

---

### Alert Providers (`src/services/alert_providers.py`)

#### Webhook Provider

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Webhook connection error | Warning | Medium | Network/DNS failure | Check URL, DNS, firewall |
| Webhook timeout | Warning | Medium | Endpoint too slow | Increase timeout, optimize endpoint |
| Webhook HTTP error (4xx/5xx) | Warning | Medium | Endpoint rejected request | Check endpoint logs, auth |
| SSRF protection blocked URL | `ValueError` | High | URL targets private IP | Use public URLs only |

---

#### Gotify Provider

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| Gotify connection error | Warning | Medium | Service unreachable | Check Gotify service, network |
| Gotify timeout | Warning | Medium | No response in time | Check Gotify health, load |
| Gotify authentication failed | Warning | High | Invalid app token | Verify token from Gotify admin |
| Gotify HTTP error | Warning | Medium | Service returned error | Check Gotify logs |

---

#### ntfy Provider

| Error | Type | Severity | Cause | Remediation |
|-------|------|----------|-------|-------------|
| ntfy connection error | Warning | Medium | Service unreachable | Check ntfy service, network |
| ntfy timeout | Warning | Medium | No response in time | Check ntfy health, load |
| ntfy HTTP error | Warning | Medium | Service returned error | Check ntfy logs, topic name |
| ntfy topic invalid | `ValueError` | Medium | Topic contains invalid chars | Use alphanumeric + dash/underscore |

---

## Error Matrix

### Severity Levels

| Severity | Impact | Example | Response Time |
|----------|--------|---------|---------------|
| **Critical** | Service cannot start or is completely broken | Missing API key, port conflict | Immediate (blocks deployment) |
| **High** | Core functionality fails but service continues | Exporter failure, database locked | Within hours (same day) |
| **Medium** | Degraded functionality or performance impact | Alert send failure, config validation | Within days (this week) |
| **Low** | Minor issues, warnings, edge cases | Pruning failed, label cardinality | When convenient (backlog) |

---

### Error Categories

| Category | Examples | Typical Cause | Prevention |
|----------|----------|---------------|-----------|
| **Configuration** | Missing env var, invalid values | Deployment error, typo | Validate config before deployment |
| **Network** | Connection error, timeout, DNS | Infrastructure issue | Health checks, retry logic |
| **Filesystem** | Permission denied, disk full | Resource exhaustion | Monitor disk space, permissions |
| **Database** | Lock timeout, corruption, full | Concurrent access, disk issue | WAL mode, backups, monitoring |
| **Validation** | Out of range, wrong type | User input error | Client-side validation, schema |
| **Programming** | Type error, logic error | Bug in code | Unit tests, static analysis |

---

### Recovery Strategies by Error Type

| Error Type | Strategy | Implementation |
|------------|----------|----------------|
| **Transient Network** | Retry with backoff | `speedtest_runner.py` (1 retry) |
| **Configuration Invalid** | Fallback to default | `runtime_config.py` validation |
| **Partial Failure** | Continue with successful | `result_dispatcher.py` |
| **Filesystem Error** | Graceful degradation | CSV prune failure non-fatal |
| **Resource Exhaustion** | Rate limiting, cleanup | Alert cooldown, pruning |
| **Corruption** | Atomic operations | Runtime config atomic write |

---

## Monitoring & Alerts

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Consecutive speedtest failures** | ≥3 | Alert configured via API |
| **Exporter failure rate** | >10% | Check exporter health |
| **Database size** | >1GB | Enable pruning or manual cleanup |
| **CSV file size** | >100MB | Enable pruning or rotation |
| **Alert send failure rate** | >50% | Check provider connectivity |
| **API error rate (5xx)** | >1% | Review logs, check resources |
| **Disk usage** | >80% | Free space or expand volume |

---

### Log Analysis Commands

```bash
# Find all errors in last hour
docker-compose logs --since=1h | grep ERROR

# Count errors by type
docker-compose logs | grep ERROR | cut -d' ' -f5- | sort | uniq -c | sort -nr

# Find database lock errors
docker-compose logs | grep "Database locked"

# Find authentication failures
docker-compose logs | grep "Invalid API key"

# Find alert failures
docker-compose logs | grep "Alert.*failed"
```

---

## Troubleshooting Flowcharts

### Speedtest Failures

```
Speedtest fails
├─ Error: "command not found"
│  └─ Fix: Install speedtest-cli
├─ Error: "timed out"
│  └─ Check: Internet connectivity, ISP throttling
├─ Error: "JSON parse failed"
│  └─ Fix: Update speedtest-cli
└─ Multiple consecutive failures
   └─ Action: Investigate ISP outage, check alerts
```

---

### Exporter Failures

```
Exporter fails
├─ CSV Exporter
│  ├─ Error: "Permission denied"
│  │  └─ Fix: Check logs/ directory permissions
│  └─ Error: "Disk full"
│     └─ Fix: Free space or enable pruning
├─ Prometheus Exporter
│  ├─ Error: "Port in use"
│  │  └─ Fix: Use different port or kill process
│  └─ Error: "Update gauges failed"
│     └─ Check: Result data validity
├─ Loki Exporter
│  ├─ Error: "Connection error"
│  │  └─ Check: Loki service, network, DNS
│  └─ Error: "Push rejected"
│     └─ Check: Loki logs, auth, tenant
└─ SQLite Exporter
   ├─ Error: "Database locked"
   │  └─ Fix: Reduce page_size, check long queries
   └─ Error: "Write failed"
      └─ Check: Disk space, permissions, integrity
```

---

### API Authentication Failures

```
API request fails
├─ Status: 401 (Unauthorized)
│  └─ Fix: Add X-Api-Key header
├─ Status: 403 (Forbidden)
│  └─ Fix: Verify API key matches .env
└─ Status: 429 (Rate Limited)
   └─ Fix: Reduce request frequency, implement backoff
```

---

## Related Documentation

- [Error Message Reference](error-messages.md) — Detailed error descriptions with examples
- [Error Handling Conventions](error-handling-conventions.md) — Patterns and best practices
- [Architecture](architecture.md) — System design and error boundaries
- [API Reference](api-reference.md) — API endpoints and error responses
- [Getting Started](getting-started.md) — Configuration and setup

---

## Document History

- **2026-05-01:** Initial documentation (M4 from ERROR-HANDLING-REVIEW.md)
