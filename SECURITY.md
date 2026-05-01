# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

**Note:** Only the latest minor version within a major release receives security updates. We
recommend upgrading to the latest release as soon as possible.

---

## Reporting a Vulnerability

We take the security of Hermes seriously. If you discover a security vulnerability, please follow these steps:

### 🔒 Private Disclosure (Preferred)

**DO NOT** open a public GitHub issue for security vulnerabilities.

**Report via:**

- **GitHub Security Advisories**: Use the "Security" tab → "Report a vulnerability"
- **Email**: <fabell.4@greenflametech.com>

**Include in your report:**

- Description of the vulnerability
- Steps to reproduce the issue
- Affected versions (if known)
- Potential impact assessment
- Any proof-of-concept code (if applicable)

### What to Expect

1. **Acknowledgment**: Within 48 hours, we'll confirm receipt of your report
2. **Triage**: Within 5 business days, we'll assess the severity and impact
3. **Updates**: We'll keep you informed of progress every 7 days minimum
4. **Resolution**: We aim to release a patch within 30 days for critical issues
5. **Credit**: With your permission, we'll credit you in the security advisory

### Coordinated Disclosure

We follow a coordinated disclosure policy:

- We'll work with you to understand and address the issue
- We'll notify you before public disclosure
- Typical embargo period: 90 days (negotiable for complex issues)
- Public disclosure occurs after patch release

---

## Security Update Policy

### Severity Levels

We use the following severity classifications:

- **Critical**: Remote code execution, authentication bypass, privilege escalation
- **High**: SQL injection, SSRF, XSS in admin context, sensitive data exposure
- **Medium**: Information disclosure, denial of service, CSRF
- **Low**: Security misconfigurations, weak cipher suites (when alternatives exist)

### Patch Release Timeline

- **Critical**: Emergency patch within 7 days
- **High**: Patch within 30 days
- **Medium**: Patch in next planned release (typically 60-90 days)
- **Low**: Addressed in next minor version

### Notification Channels

Security advisories are published via:

1. [GitHub Security Advisories](https://github.com/fabell4/hermes/security/advisories)
2. Release notes in [CHANGELOG.md](CHANGELOG.md)
3. GitHub Discussions (for post-patch discussion)

---

## Out of Scope

The following issues are **not** considered security vulnerabilities:

### User Configuration Issues

- Self-inflicted misconfigurations (e.g., disabling API key authentication)
- Running Hermes as root user (documented against in deployment guides)
- Exposing the API to the internet without reverse proxy
- Using weak API keys (minimum 32 characters enforced)

### Denial of Service

- Resource exhaustion from legitimate API use (rate limiting is documented)
- High-volume speed tests impacting network performance (user-controlled)

### Third-Party Dependencies

- Vulnerabilities in third-party Python packages (requests, FastAPI, etc.)
- Issues in user-specified alert endpoints (Webhook URLs, etc.)
- Vulnerabilities in Prometheus/Loki/Grafana (separate projects)
- Vulnerabilities in the Ookla speedtest CLI binary (external binary, updated via package manager)

### Low-Impact Findings

- Version disclosure in HTTP headers (intended for debugging)
- Verbose error messages in logs (required for troubleshooting)
- Missing security headers on health check endpoint (`/health`)

### Test Code

- Security issues only exploitable in test environments
- Hardcoded credentials in `tests/` directory (not used in production)

---

## Security Best Practices

For secure deployment of Hermes, please refer to:

- [Security Documentation](https://fabell4.github.io/hermes/security.html)
- [Security Audit Report](docs/SECURITY-AUDIT.md)
- [Deployment Guide](https://fabell4.github.io/hermes/getting-started.html)

### Quick Security Checklist

- ✅ Set a strong `API_KEY` (minimum 32 characters)
- ✅ Use HTTPS via reverse proxy (Caddy, nginx, Traefik)
- ✅ Enable rate limiting on the API endpoint
- ✅ Validate alert provider URLs (SSRF protection is built-in)
- ✅ Run containers as non-root user (default in our Docker images)
- ✅ Keep Hermes updated to the latest version

---

## Security Features

Hermes includes the following security protections:

- **API Key Authentication**: Required for all configuration and trigger endpoints
- **Rate Limiting**: Sliding window algorithm, configurable per-endpoint
- **SSRF Protection**: Validates all outbound HTTP requests (alert providers)
- **Request Size Limits**: 1 MB maximum body size (configurable)
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **Input Validation**: Pydantic models with strict type checking
- **CORS Controls**: Configurable allowed origins

For details, see [docs/SECURITY-ENHANCEMENTS.md](docs/SECURITY-ENHANCEMENTS.md).

---

## Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

<!-- Contributors will be listed here after coordinated disclosure -->

*No vulnerabilities reported yet.*

---

## Contact

For security-related questions (not vulnerability reports):

- Open a [GitHub Discussion](https://github.com/fabell4/hermes/discussions)
- Tag your discussion with the `security` label

For urgent security matters requiring private communication, use the reporting channels listed above.

---

Thank you for helping keep Hermes and our users safe! 🔒
