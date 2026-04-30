# API Reference

Complete REST API documentation for the Hermes FastAPI backend.

---

## Base URL

```
http://localhost:8080/api
```

Replace `localhost:8080` with your server address.

---

## Authentication

### API Key Authentication

When `API_KEY` is set in environment variables, **protected endpoints** require an `X-Api-Key` header:

```bash
curl -X POST http://localhost:8080/api/trigger \
  -H "X-Api-Key: your-api-key-here"
```

**Public endpoints** (GET requests) do not require authentication.

### Generate Secure API Key

```bash
# Option 1: Python secrets module (recommended)
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Option 2: OpenSSL
openssl rand -hex 32
```

**Requirements:**
- Minimum 32 characters (enforced at startup)
- Application exits with error if `API_KEY` is set but too short

### Disabling Authentication

Leave `API_KEY` unset in `.env` to disable authentication entirely. **Not recommended for production.**

---

## Rate Limiting

Protected endpoints are rate-limited per API key:
- **Default:** 60 requests per 60-second sliding window
- **Configurable:** Set `RATE_LIMIT_PER_MINUTE` in `.env`
- **Response on limit:** `429 Too Many Requests` with `Retry-After` header

**Example rate limit response:**

```bash
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

---

## Public Endpoints

### Health Check

Get API health and scheduler status.

**Request:**
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "scheduler_running": true,
  "uptime_seconds": 3600,
  "last_test_timestamp": "2026-04-29T12:00:00Z"
}
```

**Status Codes:**
- `200 OK` — API healthy

---

### Get Results (Paginated)

Retrieve speed test results with pagination. Reads from SQLite if available, falls back to CSV.

**Request:**
```http
GET /api/results?page=1&page_size=50
```

**Query Parameters:**
- `page` (optional, default: `1`) — Page number (1-indexed)
- `page_size` (optional, default: `50`) — Results per page (max: 1000)

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "timestamp": "2026-04-29T12:00:00Z",
      "download_mbps": 250.5,
      "upload_mbps": 35.2,
      "ping_ms": 15.3,
      "jitter_ms": 2.1,
      "isp": "Comcast"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 500,
    "total_pages": 10
  },
  "source": "sqlite"
}
```

**Status Codes:**
- `200 OK` — Results returned
- `404 Not Found` — Page out of range or no results available

**cURL Example:**
```bash
curl http://localhost:8080/api/results?page=1&page_size=100
```

---

### Get Latest Result

Retrieve the most recent speed test result.

**Request:**
```http
GET /api/results/latest
```

**Response:**
```json
{
  "id": 123,
  "timestamp": "2026-04-29T12:00:00Z",
  "download_mbps": 250.5,
  "upload_mbps": 35.2,
  "ping_ms": 15.3,
  "jitter_ms": 2.1,
  "isp": "Comcast"
}
```

**Status Codes:**
- `200 OK` — Result returned
- `404 Not Found` — No results available

**cURL Example:**
```bash
curl http://localhost:8080/api/results/latest
```

---

### Get Configuration

Retrieve current runtime configuration (interval, enabled exporters).

**Request:**
```http
GET /api/config
```

**Response:**
```json
{
  "speedtest_interval_minutes": 60,
  "enabled_exporters": ["csv", "sqlite", "prometheus"]
}
```

**Status Codes:**
- `200 OK` — Configuration returned

**cURL Example:**
```bash
curl http://localhost:8080/api/config
```

---

### Get Alert Configuration

Retrieve current alert settings and provider configuration.

**Request:**
```http
GET /api/alerts
```

**Response:**
```json
{
  "enabled": true,
  "failure_threshold": 3,
  "cooldown_minutes": 60,
  "providers": {
    "webhook": {
      "enabled": false,
      "url": ""
    },
    "gotify": {
      "enabled": false,
      "url": "",
      "token": "",
      "priority": 5
    },
    "ntfy": {
      "enabled": true,
      "url": "https://ntfy.sh",
      "topic": "hermes_alerts",
      "token": "",
      "priority": 3,
      "tags": "warning,rotating_light"
    },
    "apprise": {
      "enabled": false,
      "url": "",
      "urls": []
    }
  }
}
```

**Status Codes:**
- `200 OK` — Configuration returned

**cURL Example:**
```bash
curl http://localhost:8080/api/alerts
```

---

### Check Trigger Status

Check if a speed test is currently running.

**Request:**
```http
GET /api/trigger/status
```

**Response:**
```json
{
  "running": false,
  "last_trigger_time": "2026-04-29T11:55:00Z"
}
```

**Status Codes:**
- `200 OK` — Status returned

**cURL Example:**
```bash
curl http://localhost:8080/api/trigger/status
```

---

## Protected Endpoints

Require `X-Api-Key` header when `API_KEY` environment variable is set.

### Trigger Speed Test

Manually trigger a speed test to run immediately.

**Request:**
```http
POST /api/trigger
```

**Headers:**
```
X-Api-Key: your-api-key-here
```

**Response:**
```json
{
  "status": "triggered",
  "message": "Speed test will run shortly"
}
```

**Status Codes:**
- `200 OK` — Test triggered successfully
- `401 Unauthorized` — Missing or invalid API key
- `429 Too Many Requests` — Rate limit exceeded
- `503 Service Unavailable` — Test already running

**cURL Example:**
```bash
curl -X POST http://localhost:8080/api/trigger \
  -H "X-Api-Key: your-api-key-here"
```

---

### Update Configuration

Update runtime configuration (interval, enabled exporters).

**Request:**
```http
PUT /api/config
Content-Type: application/json
```

**Headers:**
```
X-Api-Key: your-api-key-here
Content-Type: application/json
```

**Body:**
```json
{
  "speedtest_interval_minutes": 30,
  "enabled_exporters": ["csv", "sqlite", "prometheus", "loki"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated successfully",
  "config": {
    "speedtest_interval_minutes": 30,
    "enabled_exporters": ["csv", "sqlite", "prometheus", "loki"]
  }
}
```

**Validation:**
- `speedtest_interval_minutes` must be between 1 and 1440 (24 hours)
- `enabled_exporters` must be a list containing valid exporters: `csv`, `sqlite`, `prometheus`, `loki`

**Status Codes:**
- `200 OK` — Configuration updated
- `400 Bad Request` — Invalid input
- `401 Unauthorized` — Missing or invalid API key
- `429 Too Many Requests` — Rate limit exceeded

**cURL Example:**
```bash
curl -X PUT http://localhost:8080/api/config \
  -H "X-Api-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "speedtest_interval_minutes": 30,
    "enabled_exporters": ["csv", "sqlite"]
  }'
```

---

### Update Alert Configuration

Update alert settings and provider configuration.

**Request:**
```http
PUT /api/alerts
Content-Type: application/json
```

**Headers:**
```
X-Api-Key: your-api-key-here
Content-Type: application/json
```

**Body:**
```json
{
  "enabled": true,
  "failure_threshold": 3,
  "cooldown_minutes": 60,
  "providers": {
    "webhook": {
      "enabled": false,
      "url": ""
    },
    "ntfy": {
      "enabled": true,
      "url": "https://ntfy.sh",
      "topic": "hermes_alerts",
      "token": "",
      "priority": 3,
      "tags": "warning,rotating_light"
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Alert configuration updated successfully"
}
```

**Validation:**
- `failure_threshold` must be >= 0 (0 = disabled)
- `cooldown_minutes` must be >= 1
- Alert URLs validated for SSRF protection (see [Security](security))
- Provider-specific validation (priority ranges, required fields)

**Status Codes:**
- `200 OK` — Configuration updated
- `400 Bad Request` — Invalid input or SSRF risk detected
- `401 Unauthorized` — Missing or invalid API key
- `429 Too Many Requests` — Rate limit exceeded

**cURL Example:**
```bash
curl -X PUT http://localhost:8080/api/alerts \
  -H "X-Api-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "failure_threshold": 3,
    "cooldown_minutes": 60,
    "providers": {
      "ntfy": {
        "enabled": true,
        "url": "https://ntfy.sh",
        "topic": "hermes_alerts",
        "priority": 3
      }
    }
  }'
```

---

### Test Alert Notification

Send a test notification to all enabled alert providers.

**Request:**
```http
POST /api/alerts/test
```

**Headers:**
```
X-Api-Key: your-api-key-here
```

**Response:**
```json
{
  "status": "success",
  "message": "Test alert sent successfully to 2 provider(s)",
  "results": {
    "webhook": true,
    "ntfy": true,
    "gotify": false,
    "apprise": false
  }
}
```

**Rate Limiting:**
- Test alerts are rate-limited globally (10-second cooldown)
- Separate from per-API-key rate limits
- Prevents notification spam

**Status Codes:**
- `200 OK` — Test sent (check `results` for per-provider status)
- `401 Unauthorized` — Missing or invalid API key
- `429 Too Many Requests` — Test alert cooldown active (wait 10 seconds)

**cURL Example:**
```bash
curl -X POST http://localhost:8080/api/alerts/test \
  -H "X-Api-Key: your-api-key-here"
```

---

## Error Responses

All errors return JSON with `detail` field:

### 400 Bad Request
```json
{
  "detail": "speedtest_interval_minutes must be between 1 and 1440"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found
```json
{
  "detail": "No results found"
}
```

### 413 Payload Too Large
```json
{
  "detail": "Request body exceeds maximum size of 1048576 bytes"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```
Response includes `Retry-After` header with seconds to wait.

### 503 Service Unavailable
```json
{
  "detail": "Speed test already running"
}
```

---

## Security Features

### SSRF Protection

Alert URLs are validated to prevent Server-Side Request Forgery attacks:

**Blocked:**
- Non-HTTP schemes: `file://`, `ftp://`, `data://`
- Localhost: `localhost`, `127.0.0.1`, `::1`
- Private IP ranges: `10.x`, `192.168.x`, `172.16-31.x`
- Link-local: `169.254.x`, `fe80::/10`
- Cloud metadata endpoints: `169.254.169.254`

**Allowed:**
- Public HTTPS/HTTP URLs only

See [Security Guide](security) for details.

### Security Headers

All responses include security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Cross-Origin-Resource-Policy: same-origin`
- `Referrer-Policy: strict-origin-when-cross-origin`

### CORS Configuration

CORS is configured via `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS=https://your-frontend-domain.com
```

**Allowed methods:** GET, POST, PUT  
**Allowed headers:** Content-Type, X-Api-Key

---

## API Client Examples

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8080/api"
API_KEY = "your-api-key-here"

# Get latest result
response = requests.get(f"{BASE_URL}/results/latest")
result = response.json()
print(f"Download: {result['download_mbps']} Mbps")

# Trigger test
response = requests.post(
    f"{BASE_URL}/trigger",
    headers={"X-Api-Key": API_KEY}
)
print(response.json())

# Update config
response = requests.put(
    f"{BASE_URL}/config",
    headers={
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "speedtest_interval_minutes": 30,
        "enabled_exporters": ["csv", "sqlite"]
    }
)
print(response.json())
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8080/api";
const API_KEY = "your-api-key-here";

// Get latest result
const response = await fetch(`${BASE_URL}/results/latest`);
const result = await response.json();
console.log(`Download: ${result.download_mbps} Mbps`);

// Trigger test
const triggerResponse = await fetch(`${BASE_URL}/trigger`, {
  method: "POST",
  headers: {
    "X-Api-Key": API_KEY
  }
});
console.log(await triggerResponse.json());

// Update config
const configResponse = await fetch(`${BASE_URL}/config`, {
  method: "PUT",
  headers: {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    speedtest_interval_minutes: 30,
    enabled_exporters: ["csv", "sqlite"]
  })
});
console.log(await configResponse.json());
```

### Bash (curl)

```bash
#!/bin/bash

BASE_URL="http://localhost:8080/api"
API_KEY="your-api-key-here"

# Get latest result
curl -s "$BASE_URL/results/latest" | jq .

# Trigger test
curl -X POST "$BASE_URL/trigger" \
  -H "X-Api-Key: $API_KEY"

# Update config
curl -X PUT "$BASE_URL/config" \
  -H "X-Api-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "speedtest_interval_minutes": 30,
    "enabled_exporters": ["csv", "sqlite"]
  }'

# Get paginated results
curl -s "$BASE_URL/results?page=1&page_size=100" | jq .
```

---

## WebSocket Support

Hermes does not currently support WebSocket connections. For real-time updates:

**Option 1:** Poll `/api/results/latest` periodically
```javascript
setInterval(async () => {
  const response = await fetch("/api/results/latest");
  const result = await response.json();
  updateUI(result);
}, 30000); // Poll every 30 seconds
```

**Option 2:** Poll `/api/trigger/status` to detect test completion
```javascript
async function waitForTestCompletion() {
  while (true) {
    const response = await fetch("/api/trigger/status");
    const status = await response.json();
    if (!status.running) break;
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  // Fetch new result
  const result = await fetch("/api/results/latest");
  return result.json();
}
```

---

## See Also

- [Getting Started](getting-started) — Deployment and authentication setup
- [Security Guide](security) — API key best practices, SSRF protection
- [Alert Configuration](alerts) — Webhook and notification provider setup
- [Architecture](architecture) — API container design and data flow
