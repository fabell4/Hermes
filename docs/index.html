# Hermes Documentation

**Hermes** is a self-hosted speed test monitoring solution that periodically tests your internet connection and exports results to multiple destinations (CSV, SQLite, Prometheus, Loki). It includes a modern React frontend for visualization and configuration.

## Quick Links

- [GitHub Repository](https://github.com/fabell4/hermes)
- [Docker Image](https://github.com/fabell4/hermes/pkgs/container/hermes)
- [Full README](https://github.com/fabell4/hermes/blob/main/README.md)

## Features

### Data Collection & Export
- **Scheduled Speed Tests** — Runs tests at configurable intervals
- **Multiple Exporters** — CSV, SQLite, Prometheus, Loki
- **Manual Triggers** — On-demand tests via UI or API
- **Data Retention** — Configurable row limits and retention periods

### Alert Notifications
Send notifications when speed tests fail consecutively:
- **Webhook** — POST to any HTTP endpoint
- **Gotify** — Self-hosted push notifications
- **ntfy** — Simple pub-sub notifications
- **Apprise** — 100+ services (Discord, Telegram, Slack, Email, SMS, etc.)

Alert configuration supports:
- Failure threshold (consecutive failures before alerting)
- Cooldown period (minimum time between alerts)
- Per-provider settings (URLs, tokens, priorities)
- Test notifications to verify setup

### Web Interface
- **Dashboard** — Real-time charts and statistics
- **Settings** — Configure intervals, exporters, and alerts
- **API** — REST endpoints for automation

## Alert Setup Examples

### Apprise (Recommended)

**With persistent config:**
```bash
# Deploy Apprise API container
docker run -d -p 8000:8000 caronc/apprise-api

# Configure in Hermes
ALERT_APPRISE_URL=https://apprise.example.com/notify/myconfig
```

Then manage recipients in Apprise's web UI at `http://apprise.example.com`.

**With stateless mode:**
```bash
ALERT_APPRISE_URL=https://apprise.example.com
```

Add service URLs in the UI Settings → Apprise → Service URLs:
```
ntfys://ntfy.example.com/topic?token=tk_xxx
gotify://gotify.example.com/token
discord://webhook_id/webhook_token
```

### ntfy

```bash
ALERT_NTFY_TOPIC=hermes_alerts
ALERT_NTFY_TOKEN=tk_xxxxxxxxxxxxx  # Optional for private topics
ALERT_NTFY_PRIORITY=3
```

### Gotify

```bash
ALERT_GOTIFY_URL=https://gotify.example.com
ALERT_GOTIFY_TOKEN=your_app_token
ALERT_GOTIFY_PRIORITY=5
```

### Webhook

```bash
ALERT_WEBHOOK_URL=https://your-webhook.example.com/alerts
```

Payload format:
```json
{
  "failure_count": 3,
  "last_error": "Connection timeout",
  "timestamp": "2026-04-29T12:00:00Z"
}
```

## Deployment

See the [main README](https://github.com/fabell4/hermes/blob/main/README.md) for full deployment instructions with Docker Compose.

## Support

- Report issues on [GitHub Issues](https://github.com/fabell4/hermes/issues)
- View changelog at [CHANGELOG.md](https://github.com/fabell4/hermes/blob/main/CHANGELOG.md)