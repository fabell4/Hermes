# Security Guide

Hermes implements multiple layers of security for production deployments. This guide covers security features, best practices, and audit reports.

---

## Security Features

### API Key Authentication

**Purpose:** Protect write endpoints from unauthorized access.

**Implementation:**
- Optional `API_KEY` environment variable
- **32-character minimum** enforced at startup (application exits if too short)
- Timing-safe comparison using `secrets.compare_digest()` to prevent timing attacks
- `X-Api-Key` header required on all protected endpoints

**Protected Endpoints:**
- `POST /api/trigger` — Manual speed test trigger
- `PUT /api/config` — Configuration updates
- `PUT /api/alerts` — Alert configuration updates
- `POST /api/alerts/test` — Test alert notifications

**Public Endpoints:** (no authentication required)
- `GET /api/health` — Health check
- `GET /api/results` — Speed test results
- `GET /api/results/latest` — Latest result
- `GET /api/config` — Current configuration
- `GET /api/alerts` — Alert configuration
- `GET /api/trigger/status` — Test status

**Generate Secure Key:**
```bash
# Recommended: Python secrets module
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Alternative: OpenSSL
openssl rand -hex 32
```

**Startup Validation:**
```
ERROR: API_KEY must be at least 32 characters long
Suggestion: Generate a secure key with:
  python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

---

### Rate Limiting

**Purpose:** Prevent abuse and DoS attacks via request flooding.

**Implementation:**
- Per-API-key sliding window rate limiting
- **Default:** 60 requests per 60-second window (configurable via `RATE_LIMIT_PER_MINUTE`)
- Applies to protected endpoints only
- Returns `429 Too Many Requests` with `Retry-After` header

**Example Response:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

**Configuration:**
```bash
RATE_LIMIT_PER_MINUTE=120  # Allow 120 requests per 60 seconds
```

**Test Alert Rate Limiting:**
- Test alerts (`POST /api/alerts/test`) have **10-second global cooldown**
- Separate from per-API-key limits
- Prevents notification spam during configuration testing

---

### SSRF Protection

**Purpose:** Prevent Server-Side Request Forgery attacks via alert URLs.

**Implementation:**
- **URL validation** on all alert webhook/Gotify/ntfy/Apprise URLs
- Blocks internal network access, cloud metadata endpoints, and non-HTTP schemes

**Blocked Targets:**

| Category | Examples | Reason |
|---|---|---|
| **Non-HTTP schemes** | `file://`, `ftp://`, `data://`, `javascript:` | Prevent local file/protocol abuse |
| **Localhost** | `localhost`, `127.0.0.1`, `::1` | Block loopback access |
| **Private IPs** | `10.x`, `192.168.x`, `172.16-31.x` | Block internal network |
| **Link-local** | `169.254.x`, `fe80::/10` | Block metadata endpoints |
| **Cloud metadata** | `169.254.169.254` | Prevent AWS/GCP/Azure credential theft |

**Allowed Targets:**
- Public HTTPS/HTTP URLs only (resolved IPs must be public)

**Validation Error:**
```json
{
  "detail": "Invalid alert URL: private IP addresses and localhost are not allowed"
}
```

**Testing:**
```bash
# Blocked - private IP
curl -X PUT http://localhost:8080/api/alerts \
  -H "X-Api-Key: key" \
  -H "Content-Type: application/json" \
  -d '{"providers": {"webhook": {"enabled": true, "url": "http://192.168.1.1/webhook"}}}'

# Allowed - public URL
curl -X PUT http://localhost:8080/api/alerts \
  -H "X-Api-Key: key" \
  -H "Content-Type: application/json" \
  -d '{"providers": {"webhook": {"enabled": true, "url": "https://webhook.site/unique-id"}}}'
```

---

### Request Size Limits

**Purpose:** Prevent DoS attacks via large request bodies.

**Implementation:**
- **1 MB default limit** (configurable via `MAX_REQUEST_BODY_SIZE`)
- Middleware checks `Content-Length` header before reading body
- Returns `413 Payload Too Large` if exceeded

**Configuration:**
```bash
MAX_REQUEST_BODY_SIZE=524288  # 512 KB limit
```

**Error Response:**
```json
{
  "detail": "Request body exceeds maximum size of 1048576 bytes"
}
```

---

### Security Headers

**Purpose:** Protect against common web vulnerabilities (clickjacking, MIME sniffing, etc.).

**Middleware:** `SecurityHeadersMiddleware` adds headers to all responses.

**Headers:**

| Header | Value | Purpose |
|---|---|---|
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `Cross-Origin-Resource-Policy` | `same-origin` | Restrict resource loading |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer information |

**Verification:**
```bash
curl -I http://localhost:8080/api/health
```

---

### CORS Configuration

**Purpose:** Restrict which frontend origins can access the API.

**Implementation:**
- Configurable via `CORS_ORIGINS` environment variable (comma-separated)
- **Default:** `http://localhost:5173,http://localhost:4173` (Vite dev servers)
- Restricted methods: `GET`, `POST`, `PUT`
- Restricted headers: `Content-Type`, `X-Api-Key`

**Configuration:**
```bash
# Production: restrict to your domain only
CORS_ORIGINS=https://your-frontend-domain.com

# Development: allow multiple origins
CORS_ORIGINS=http://localhost:5173,http://localhost:4173,https://staging.example.com
```

**Preflight Request:**
```bash
curl -X OPTIONS http://localhost:8080/api/config \
  -H "Origin: https://your-frontend-domain.com" \
  -H "Access-Control-Request-Method: PUT"
```

---

### Input Validation

**Purpose:** Prevent injection attacks and ensure data integrity.

**Implementation:**
- **Pydantic models** enforce strict type checking on all API inputs
- Range validation (e.g., `speedtest_interval_minutes` between 1 and 1440)
- Required field validation
- Type coercion with validation errors

**Examples:**

**Valid Configuration Update:**
```json
{
  "speedtest_interval_minutes": 30,
  "enabled_exporters": ["csv", "sqlite"]
}
```

**Invalid Configuration Update:**
```json
{
  "speedtest_interval_minutes": 0,  // Too low
  "enabled_exporters": "csv"  // Wrong type (should be list)
}
```

**Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "speedtest_interval_minutes"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

---

## Security Best Practices

### For Production Deployments

#### 1. Always Set API_KEY

Generate a strong, unique API key:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Add to `.env`:
```bash
API_KEY=your-generated-key-here
```

**Never commit API keys to version control.**

#### 2. Use HTTPS

Deploy behind a reverse proxy (nginx, Caddy, Traefik) with TLS certificates:

**nginx example:**
```nginx
server {
    listen 443 ssl http2;
    server_name hermes.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/hermes.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hermes.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Caddy example:**
```
hermes.yourdomain.com {
    reverse_proxy localhost:8080
}
```

#### 3. Restrict CORS Origins

Set `CORS_ORIGINS` to your frontend domain only:

```bash
CORS_ORIGINS=https://your-frontend-domain.com
```

**Never use `*` in production.**

#### 4. Configure Rate Limits

Adjust `RATE_LIMIT_PER_MINUTE` based on your usage patterns:

```bash
# Low traffic: tighten limits
RATE_LIMIT_PER_MINUTE=30

# High traffic: increase limits
RATE_LIMIT_PER_MINUTE=120
```

#### 5. Validate Alert URLs

Only use trusted, public HTTPS endpoints for alert webhooks:

**Good:**
```bash
ALERT_WEBHOOK_URL=https://webhook.site/unique-id
ALERT_GOTIFY_URL=https://gotify.yourdomain.com
```

**Bad (blocked by SSRF protection):**
```bash
ALERT_WEBHOOK_URL=http://localhost:8080/admin
ALERT_WEBHOOK_URL=http://192.168.1.100/internal
```

#### 6. Network Isolation

Deploy in a private network segment if possible:

**docker-compose.yml:**
```yaml
services:
  hermes-scheduler:
    networks:
      - hermes_internal
  hermes-api:
    networks:
      - hermes_internal
    ports:
      - "127.0.0.1:8080:8080"  # Bind to localhost only

networks:
  hermes_internal:
    driver: bridge
    internal: true  # No external access
```

Then expose via reverse proxy on host network.

#### 7. Monitor Logs

Review authentication failures and rate limit violations regularly:

```bash
# Check for auth failures
docker logs hermes-api | grep -i "unauthorized\|invalid api key"

# Check for rate limit hits
docker logs hermes-api | grep -i "rate limit"

# Check for SSRF attempts
docker logs hermes-api | grep -i "ssrf\|invalid alert url"
```

#### 8. Keep Docker Images Updated

Regularly pull latest images to get security patches:

```bash
docker compose pull
docker compose up -d
```

Subscribe to GitHub releases for notifications:
https://github.com/fabell4/hermes/releases

#### 9. Use Read-Only Volumes (Optional)

For extra security, mount sensitive files as read-only:

```yaml
volumes:
  - ./config.json:/app/data/config.json:ro
```

#### 10. Run as Non-Root User

Dockerfile already uses non-root user (`appuser`), but verify:

```bash
docker exec hermes-api whoami
# Output: appuser
```

---

## Security Documentation

### Security Audit Report

**[Security Audit Report](SECURITY-AUDIT)** — Comprehensive 50-page security analysis covering:

- **Authentication Review** — API key validation, timing attacks, credential storage
- **Rate Limiting Analysis** — Sliding window implementation, DoS protection, Retry-After headers
- **Input Validation** — Pydantic schemas, boundary conditions, type safety
- **SSRF Assessment** — URL validation, private IP blocking, cloud metadata protection
- **Threat Modeling** — Attack scenarios, mitigation strategies, risk ratings
- **Recommendations Summary** — Prioritized security enhancements

**Conclusion:** *"APPROVED FOR v1.0 RELEASE after implementing SSRF protection and API key length validation"* (both complete).

### Security Enhancements Summary

**[Security Enhancements](SECURITY-ENHANCEMENTS)** — Implementation details of v1.0 security fixes:

1. **API Key Validation** — 32-character minimum enforced at startup
2. **SSRF Protection** — Alert URL validation blocking dangerous targets
3. **Rate Limiting Improvements** — Retry-After headers, test alert cooldown
4. **Security Headers** — X-Frame-Options, Referrer-Policy added

**Test Coverage:** 130+ API security tests validating all features.

---

## Test Coverage

### Security-Focused Tests

| Test Suite | Count | Coverage |
|---|---|---|
| **SSRF Protection** | 15 | Valid URLs, dangerous schemes, localhost, private IPs, link-local, multiple providers |
| **Request Size Limits** | 6 | Under/at/over limit, missing Content-Length, error messages |
| **Test Alert Rate Limiting** | 7 | First allowed, second rejected, cooldown behavior, Retry-After header |
| **Authentication** | 25+ | Missing key, invalid key, valid key, timing-safe comparison |
| **Rate Limiting** | 18+ | Per-key limits, sliding window, Retry-After header, burst behavior |
| **Input Validation** | 30+ | Type checking, range validation, required fields, boundary conditions |
| **API Boundaries** | 25+ | Paginations, invalid pages, empty results, malformed queries |

**Total API Tests:** 344 passing  
**Code Coverage:** 92% (1,395 statements, 114 missed)  
**Linting:** All ruff checks passing

**Run Tests:**
```bash
pytest --cov=src tests/
```

---

## Vulnerability Disclosure

### Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Instead:**
1. Email security report to: [maintainer-email]
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Affected versions
   - Suggested fix (if known)

Response SLA: 48 hours for acknowledgment, 7 days for fix timeline.

### Security Updates

Security patches are released as:
- **Patch releases** for critical vulnerabilities (e.g., v1.0.1)
- **Changelog entries** with `[SECURITY]` prefix
- **GitHub Security Advisories** for CVE-level issues

Subscribe to releases for notifications:
https://github.com/fabell4/hermes/releases

---

## Security Checklist

Use this checklist before deploying to production:

- [ ] `API_KEY` set to 32+ character strong key
- [ ] Running behind HTTPS reverse proxy with valid TLS certificate
- [ ] `CORS_ORIGINS` restricted to frontend domain only
- [ ] `RATE_LIMIT_PER_MINUTE` configured for expected traffic
- [ ] Alert URLs validated and HTTPS-only
- [ ] Docker images updated to latest version
- [ ] Logs monitored for auth failures and rate limit violations
- [ ] Network isolation applied (private network segment)
- [ ] Volumes mounted with appropriate permissions
- [ ] Health check endpoints verified
- [ ] Backup strategy in place for `hermes.db` and `runtime_config.json`

---

## Common Security Questions

### Q: Is it safe to disable authentication?

**A:** Only in completely isolated environments (e.g., home network with no external access). **Never disable authentication for internet-facing deployments.** Anyone can trigger speed tests and modify configuration without authentication.

### Q: Can I use the same API key across multiple deployments?

**A:** Not recommended. Each deployment should have a unique API key to prevent credential reuse and enable independent key rotation.

### Q: How do I rotate API keys?

**A:** Currently, key rotation requires:
1. Generate new key
2. Update `.env` with new key
3. Restart containers
4. Update API clients with new key

**Planned for v2.0:** Multi-key support and zero-downtime rotation.

### Q: Are API keys logged?

**A:** No. API keys are never logged or written to disk (except `.env` file). Failed authentication attempts log the error but not the attempted key.

### Q: Can I use mutual TLS (mTLS)?

**A:** Hermes doesn't natively support mTLS, but you can configure it at the reverse proxy level (nginx, Caddy, Traefik). Clients must present valid certificates to access the API.

### Q: Does Hermes support OAuth2/OIDC?

**A:** Not currently. Planned for post-v1.0 enhancements. See [TODO.md](https://github.com/fabell4/hermes/blob/main/TODO.md) for roadmap.

### Q: How are secrets stored?

**A:** All secrets (API keys, alert tokens) are stored in:
- `.env` file (plaintext, should be protected via file permissions)
- `runtime_config.json` (plaintext, alert provider tokens)

**Planned for v2.0:** Integration with secrets vaults (HashiCorp Vault, AWS Secrets Manager).

### Q: Is SQLite database encrypted?

**A:** No. The `hermes.db` file stores speed test results in plaintext. If you need encryption, use:
- **Filesystem-level encryption** (LUKS, FileVault, BitLocker)
- **Volume encryption** via Docker secrets or encrypted volumes

### Q: Can I run Hermes behind Cloudflare?

**A:** Yes. Enable Cloudflare's "Bot Fight Mode" and "Rate Limiting" for additional protection. API key authentication still applies.

---

## See Also

- [Security Audit Report](SECURITY-AUDIT) — Comprehensive security analysis
- [Security Enhancements](SECURITY-ENHANCEMENTS) — v1.0 security fixes
- [API Reference](api-reference) — Authentication and rate limiting details
- [Getting Started](getting-started) — API key generation and configuration
- [Alerts Configuration](alerts) — SSRF protection on alert URLs
