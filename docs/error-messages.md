# Error Message Reference

**Project:** Hermes Speed Monitor  
**Last Updated:** 2026-05-01  
**Purpose:** Centralized error message reference with troubleshooting steps

---

## Table of Contents

- [API Errors](#api-errors)
- [Configuration Errors](#configuration-errors)
- [Exporter Errors](#exporter-errors)
- [Alert Provider Errors](#alert-provider-errors)
- [Speedtest Errors](#speedtest-errors)
- [Dispatcher Errors](#dispatcher-errors)
- [Database Errors](#database-errors)

---

## API Errors

### Authentication & Authorization

#### `Missing X-Api-Key header`

**HTTP Status:** 401 Unauthorized  
**Source:** [src/api/auth.py](../src/api/auth.py)  
**Cause:** API request missing required `X-Api-Key` header  
**Troubleshooting:**
1. Verify API key is configured in `.env` file (`API_KEY=your-key-here`)
2. Ensure API client is sending `X-Api-Key` header with all requests
3. Check API key is not empty or whitespace-only

**Example Fix:**
```bash
# Add API key to .env
echo "API_KEY=$(openssl rand -hex 32)" >> .env

# Test with curl
curl -H "X-Api-Key: your-key-here" http://localhost:8080/api/health
```

---

#### `Invalid API key`

**HTTP Status:** 403 Forbidden  
**Source:** [src/api/auth.py](../src/api/auth.py)  
**Cause:** API key provided does not match configured key  
**Troubleshooting:**
1. Verify API key matches value in `.env` file
2. Check for leading/trailing whitespace in API key
3. Ensure API key has not been rotated without updating clients
4. Verify environment variables are loaded correctly (`docker-compose logs hermes-api`)

---

#### `Rate limit exceeded`

**HTTP Status:** 429 Too Many Requests  
**Source:** [src/api/auth.py](../src/api/auth.py)  
**Cause:** Client exceeded configured rate limit  
**Troubleshooting:**
1. Check `RATE_LIMIT_PER_MINUTE` configuration (default: 60 requests/minute)
2. Reduce request frequency or batch operations
3. Implement exponential backoff in client code
4. Consider increasing rate limit if legitimate use case requires it

**Configuration:**
```bash
# Increase rate limit (use with caution)
RATE_LIMIT_PER_MINUTE=120
```

---

### Resource Errors

#### `No database found yet`

**HTTP Status:** 503 Service Unavailable  
**Source:** [src/api/routes/results.py](../src/api/routes/results.py)  
**Cause:** SQLite database not initialized (no speedtests have run yet)  
**Troubleshooting:**
1. Wait for first speedtest to complete (check logs)
2. Manually trigger test: `POST /api/trigger`
3. Verify SQLite exporter is enabled in runtime config
4. Check filesystem permissions on data directory

**Expected Behavior:** This error is normal on first startup before the first speedtest completes.

---

#### `Failed to start manual test thread`

**HTTP Status:** 500 Internal Server Error  
**Source:** [src/api/routes/trigger.py](../src/api/routes/trigger.py)  
**Cause:** Unable to start background thread for manual speedtest  
**Troubleshooting:**
1. Check system resources (CPU, memory)
2. Review logs for thread creation errors
3. Verify no resource exhaustion (too many threads)
4. Restart container if thread pool is exhausted

---

### Configuration Endpoint Errors

#### `Invalid configuration payload`

**HTTP Status:** 400 Bad Request  
**Source:** [src/api/routes/config.py](../src/api/routes/config.py)  
**Cause:** Configuration update contains invalid values  
**Troubleshooting:**
1. Verify `interval_minutes` is between 5 and 1440
2. Ensure `enabled_exporters` is an array of valid exporter names
3. Check JSON syntax is valid
4. Review validation error details in response body

**Valid Exporter Names:**
- `csv`
- `prometheus`
- `loki`
- `sqlite`

---

### Alert Configuration Errors

#### `Threshold must be a positive integer`

**HTTP Status:** 400 Bad Request  
**Source:** [src/api/routes/alerts.py](../src/api/routes/alerts.py)  
**Cause:** Alert threshold value is invalid  
**Troubleshooting:**
1. Ensure threshold is an integer ≥ 1
2. Recommended range: 2-5 consecutive failures
3. Too low (1) may cause false positives
4. Too high (>10) may delay critical alerts

---

#### `Cooldown must be a positive integer`

**HTTP Status:** 400 Bad Request  
**Source:** [src/api/routes/alerts.py](../src/api/routes/alerts.py)  
**Cause:** Alert cooldown period is invalid  
**Troubleshooting:**
1. Ensure cooldown is an integer ≥ 1 (minutes)
2. Recommended: 60 minutes to avoid alert storms
3. Minimum: 1 minute (for testing only)

---

#### `Webhook URL must start with http:// or https://`

**HTTP Status:** 400 Bad Request  
**Source:** [src/api/routes/alerts.py](../src/api/routes/alerts.py)  
**Cause:** Webhook URL has invalid scheme  
**Troubleshooting:**
1. Ensure URL starts with `http://` or `https://`
2. No other schemes (ftp, file, etc.) are supported
3. Check for typos in URL

---

#### `Gotify/ntfy URL is required`

**HTTP Status:** 400 Bad Request  
**Source:** [src/api/routes/alerts.py](../src/api/routes/alerts.py)  
**Cause:** Alert provider enabled but URL not configured  
**Troubleshooting:**
1. Provide valid URL for alert provider
2. Verify URL is accessible from container
3. Check network connectivity to alert service

---

---

## Configuration Errors

### Runtime Configuration

#### `Runtime config validation failed`

**Level:** WARNING  
**Source:** [src/runtime_config.py](../src/runtime_config.py)  
**Cause:** Stored configuration contains invalid values  
**Troubleshooting:**
1. Check `data/runtime_config.json` for malformed JSON
2. Review validation warnings in logs
3. Delete config file to reset to defaults (make backup first)
4. Verify file permissions allow read/write

**Manual Reset:**
```bash
# Backup current config
cp data/runtime_config.json data/runtime_config.json.bak

# Reset to defaults (container will regenerate)
rm data/runtime_config.json
docker-compose restart hermes-api hermes-scheduler
```

---

#### `Could not save runtime config`

**Level:** ERROR  
**Source:** [src/runtime_config.py](../src/runtime_config.py)  
**Cause:** Failed to write configuration file  
**Troubleshooting:**
1. Check filesystem permissions on `data/` directory
2. Verify disk space is available (`df -h`)
3. Check for read-only filesystem
4. Review logs for underlying OS errors

---

#### `interval_minutes out of range`

**Level:** WARNING  
**Source:** [src/runtime_config.py](../src/runtime_config.py)  
**Cause:** Interval value outside allowed range (5-1440)  
**Troubleshooting:**
1. Ensure interval is between 5 minutes and 24 hours
2. Minimum: 5 minutes (to avoid ISP throttling)
3. Maximum: 1440 minutes (24 hours)
4. Default will be used if invalid

---

---

## Exporter Errors

### CSV Exporter

#### `CSV write failed`

**Level:** ERROR  
**Source:** [src/exporters/csv_exporter.py](../src/exporters/csv_exporter.py)  
**Cause:** Unable to write to CSV file  
**Troubleshooting:**
1. Check filesystem permissions on logs directory
2. Verify disk space available
3. Ensure CSV path is valid and writable
4. Check for file locks from other processes

---

#### `CSV prune failed`

**Level:** WARNING  
**Source:** [src/exporters/csv_exporter.py](../src/exporters/csv_exporter.py)  
**Cause:** Unable to prune old rows (non-fatal)  
**Troubleshooting:**
1. Check CSV file is not corrupted
2. Verify sufficient disk space for temp file
3. Review retention configuration
4. Note: This warning does not prevent new writes

**Note:** CSV pruning failures are non-fatal. New results will still be written.

---

### Prometheus Exporter

#### `Invalid port number`

**Level:** ERROR  
**Source:** [src/exporters/prometheus_exporter.py](../src/exporters/prometheus_exporter.py)  
**Cause:** Prometheus port is not a valid integer or is out of range  
**Troubleshooting:**
1. Verify `PROMETHEUS_PORT` is an integer (1-65535)
2. Common ports: 9090 (Prometheus), 9100 (Node Exporter), 8000-9999 (custom)
3. Ensure port is not already in use
4. Check for typos in environment variable

---

#### `Prometheus port already in use`

**Level:** ERROR  
**Source:** [src/exporters/prometheus_exporter.py](../src/exporters/prometheus_exporter.py)  
**Cause:** Another process is listening on configured port  
**Troubleshooting:**
1. Check for duplicate Hermes instances
2. Use different port: `PROMETHEUS_PORT=9091`
3. Identify conflicting process: `lsof -i :9090` (Linux) or `netstat -ano | findstr :9090` (Windows)
4. Kill conflicting process or choose different port

---

#### `Failed to update Prometheus gauges`

**Level:** ERROR  
**Source:** [src/exporters/prometheus_exporter.py](../src/exporters/prometheus_exporter.py)  
**Cause:** Error updating metrics (likely label mismatch)  
**Troubleshooting:**
1. Check result data contains all required fields
2. Review logs for label cardinality warnings
3. Verify ISP field is not excessively long
4. Restart exporter to reset metrics

---

### Loki Exporter

#### `Loki URL is required`

**Level:** ERROR  
**Source:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py)  
**Cause:** Loki exporter enabled but URL not configured  
**Troubleshooting:**
1. Set `LOKI_URL` environment variable
2. Example: `LOKI_URL=http://loki:3100`
3. Verify Loki is accessible from container
4. Test connectivity: `curl http://loki:3100/ready`

---

#### `Loki URL must use http or https`

**Level:** ERROR  
**Source:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py)  
**Cause:** Invalid URL scheme  
**Troubleshooting:**
1. Ensure URL starts with `http://` or `https://`
2. No other schemes supported (file, ftp, etc.)
3. Check for typos

---

#### `Loki push connection error`

**Level:** ERROR  
**Source:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py)  
**Cause:** Network connectivity issue to Loki  
**Troubleshooting:**
1. Verify Loki service is running
2. Check network connectivity: `docker exec hermes-scheduler curl http://loki:3100/ready`
3. Verify Docker network configuration
4. Check firewall rules
5. Review Loki logs for errors

---

#### `Loki push timed out`

**Level:** ERROR  
**Source:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py)  
**Cause:** Loki did not respond within timeout period  
**Troubleshooting:**
1. Check Loki service health and load
2. Increase timeout: `LOKI_TIMEOUT=10` (default: 5)
3. Verify network latency is acceptable
4. Review Loki resource usage (CPU, memory)
5. Check for Loki ingester backlogs

---

#### `Loki push rejected`

**Level:** ERROR  
**Source:** [src/exporters/loki_exporter.py](../src/exporters/loki_exporter.py)  
**Cause:** Loki returned HTTP error  
**Troubleshooting:**
1. Check Loki authentication if required
2. Verify push path is correct (default: `/loki/api/v1/push`)
3. Review Loki error response in logs
4. Check Loki tenant configuration if multi-tenant
5. Verify log labels are valid (no special characters)

---

### SQLite Exporter

#### `SQLite write failed`

**Level:** ERROR  
**Source:** [src/exporters/sqlite_exporter.py](../src/exporters/sqlite_exporter.py)  
**Cause:** Failed to insert row into database  
**Troubleshooting:**
1. Check filesystem permissions on data directory
2. Verify disk space available
3. Check database is not corrupted: `sqlite3 data/results.db "PRAGMA integrity_check;"`
4. Review schema migration status

---

#### `SQLite database locked (timeout after Xs)`

**Level:** ERROR  
**Source:** [src/exporters/sqlite_exporter.py](../src/exporters/sqlite_exporter.py)  
**Cause:** Database locked by another process  
**Troubleshooting:**
1. Check for long-running queries (API result endpoint with large page size)
2. Reduce page_size in API queries
3. Verify WAL mode is enabled (better concurrency)
4. Check for zombie processes holding locks: `fuser data/results.db`
5. Restart container if lock persists

**Note:** Lock timeout is configured in code (default: 30 seconds)

---

---

## Alert Provider Errors

### Generic Alert Errors

#### `Alert provider [name] failed to send`

**Level:** ERROR  
**Source:** [src/services/alert_manager.py](../src/services/alert_manager.py)  
**Cause:** Alert provider failed to send notification  
**Troubleshooting:**
1. Check provider-specific logs for details
2. Verify provider URL is accessible
3. Test provider manually (curl/API client)
4. Check network connectivity
5. Review provider authentication credentials

**Note:** Alert sending is async. Failures are logged but do not block speedtest execution.

---

### Webhook Provider

#### `Webhook delivery failed`

**Level:** ERROR  
**Source:** [src/services/alert_providers.py](../src/services/alert_providers.py)  
**Cause:** HTTP request to webhook URL failed  
**Troubleshooting:**
1. Verify webhook URL is correct and accessible
2. Check webhook endpoint logs for errors
3. Verify endpoint accepts POST with JSON payload
4. Test manually: `curl -X POST -H "Content-Type: application/json" -d '{"test": true}' YOUR_WEBHOOK_URL`
5. Check for SSRF protection blocking private IPs

---

### Gotify Provider

#### `Gotify notification failed`

**Level:** ERROR  
**Source:** [src/services/alert_providers.py](../src/services/alert_providers.py)  
**Cause:** Failed to send notification to Gotify  
**Troubleshooting:**
1. Verify Gotify URL and app token
2. Check Gotify service is running
3. Test token: `curl "http://gotify:80/message?token=YOUR_TOKEN" -F "message=test"`
4. Review Gotify logs for errors
5. Verify network connectivity from container

---

### ntfy Provider

#### `ntfy notification failed`

**Level:** ERROR  
**Source:** [src/services/alert_providers.py](../src/services/alert_providers.py)  
**Cause:** Failed to send notification to ntfy  
**Troubleshooting:**
1. Verify ntfy URL and topic name
2. Check ntfy service is running
3. Test: `curl -d "test message" http://ntfy:80/YOUR_TOPIC`
4. Review ntfy logs for errors
5. Verify topic name does not contain invalid characters

---

---

## Speedtest Errors

### Runner Errors

#### `Speedtest execution failed`

**Level:** ERROR  
**Source:** [src/services/speedtest_runner.py](../src/services/speedtest_runner.py)  
**Cause:** speedtest-cli command failed  
**Troubleshooting:**
1. Verify speedtest-cli is installed: `speedtest --version`
2. Check internet connectivity
3. Test manually: `speedtest --json`
4. Review stderr output in logs
5. Check for ISP blocking speedtest traffic

---

#### `Speedtest timed out`

**Level:** ERROR  
**Source:** [src/services/speedtest_runner.py](../src/services/speedtest_runner.py)  
**Cause:** Speedtest did not complete within timeout period  
**Troubleshooting:**
1. Increase timeout (not configurable, fixed at 120s)
2. Check for network congestion
3. Try different speedtest server
4. Verify sufficient bandwidth available
5. Check for ISP throttling

---

#### `Speedtest retry exhausted`

**Level:** ERROR  
**Source:** [src/services/speedtest_runner.py](../src/services/speedtest_runner.py)  
**Cause:** All retry attempts failed  
**Troubleshooting:**
1. Check consecutive failure count for alerting
2. Verify internet connectivity is stable
3. Review logs for underlying error patterns
4. Consider adjusting retry logic if transient errors are common

**Note:** Speedtest runner retries once on failure. If both attempts fail, the test is considered failed.

---

---

## Dispatcher Errors

### Dispatch Failures

#### `Exporter '[name]' failed`

**Level:** ERROR  
**Source:** [src/result_dispatcher.py](../src/result_dispatcher.py)  
**Cause:** One or more exporters failed during dispatch  
**Troubleshooting:**
1. Review exporter-specific error in logs
2. Check exporter configuration
3. Verify exporter dependencies are running (Loki, Prometheus)
4. Test exporter individually
5. Disable failing exporter if blocking progress

**Note:** Dispatcher continues even if one exporter fails. Partial success is possible.

---

#### `Dispatch called but no exporters are registered`

**Level:** WARNING  
**Source:** [src/result_dispatcher.py](../src/result_dispatcher.py)  
**Cause:** No exporters configured  
**Troubleshooting:**
1. Enable at least one exporter in runtime config
2. Verify `enabled_exporters` list is not empty
3. Check exporter registration in main.py
4. Review startup logs for exporter initialization

**Note:** This is a configuration issue, not an error. Add at least one exporter to store results.

---

#### `Invalid result type passed to register`

**Level:** ERROR  
**Source:** [src/result_dispatcher.py](../src/result_dispatcher.py)  
**Cause:** Attempted to register a non-exporter object  
**Troubleshooting:**
1. This is a programming error, not a configuration issue
2. Verify custom exporters inherit from `BaseExporter`
3. Review exporter registration code
4. Report bug if using only built-in exporters

---

---

## Database Errors

### Migration Errors

#### `SQLite migration failed`

**Level:** ERROR  
**Source:** [src/exporters/sqlite_exporter.py](../src/exporters/sqlite_exporter.py)  
**Cause:** Failed to initialize or migrate database schema  
**Troubleshooting:**
1. Check database file is not corrupted
2. Verify filesystem permissions
3. Review migration logic for errors
4. Backup and delete database to recreate: `mv data/results.db data/results.db.bak`

---

#### `SQLite integrity check failed`

**Level:** ERROR  
**Source:** Manual troubleshooting  
**Cause:** Database file is corrupted  
**Troubleshooting:**
1. Stop container
2. Backup database: `cp data/results.db data/results.db.bak`
3. Attempt repair: `sqlite3 data/results.db ".recover" | sqlite3 data/results_repaired.db`
4. If unrecoverable, restore from backup or start fresh

---

---

## General Troubleshooting Tips

### Logs

- **Scheduler logs:** `docker-compose logs -f hermes-scheduler`
- **API logs:** `docker-compose logs -f hermes-api`
- **Combined:** `docker-compose logs -f`

### Health Checks

- **API health:** `curl http://localhost:8080/api/health`
- **Prometheus metrics:** `curl http://localhost:9090/metrics`
- **Loki ready:** `curl http://loki:3100/ready`

### Configuration Validation

```bash
# Check runtime config
cat data/runtime_config.json | jq .

# Validate JSON syntax
jq empty data/runtime_config.json && echo "Valid JSON" || echo "Invalid JSON"
```

### Database Inspection

```bash
# Connect to SQLite database
sqlite3 data/results.db

# Check schema
.schema

# Count rows
SELECT COUNT(*) FROM speed_results;

# View latest result
SELECT * FROM speed_results ORDER BY timestamp DESC LIMIT 1;
```

### Network Debugging

```bash
# Test connectivity from scheduler container
docker exec hermes-scheduler curl -v http://loki:3100/ready

# Test external connectivity
docker exec hermes-scheduler curl -v https://www.google.com

# Check DNS resolution
docker exec hermes-scheduler nslookup loki
```

---

## Related Documentation

- [Error Handling Conventions](error-handling-conventions.md) — Exception patterns and guidelines
- [Error Catalog](error-catalog.md) — Complete list of errors by module
- [Monitoring Runbook](../README.md#troubleshooting) — Production monitoring guide
- [Architecture](architecture.md) — System design and component interaction
- [API Reference](api-reference.md) — Complete API documentation

---

## Document History

- **2026-05-01:** Initial documentation (M2 from ERROR-HANDLING-REVIEW.md)
