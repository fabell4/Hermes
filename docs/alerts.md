---
layout: default
title: "Alert Configuration"
---

# Alert Configuration

Hermes can send notifications when speed tests fail consecutively. Alerts are configurable via the UI Settings page or environment variables.

---

## Supported Alert Providers

| Provider | Description | Setup Complexity |
| --- | --- | --- |
| **Webhook** | POST JSON to any HTTP endpoint | ⭐ Simple |
| **Gotify** | Self-hosted push notifications ([gotify.net](https://gotify.net)) | ⭐⭐ Moderate |
| **ntfy** | Simple pub-sub notifications ([ntfy.sh](https://ntfy.sh)) | ⭐ Simple |
| **Apprise** | 100+ services via Apprise API ([caronc/apprise-api](https://github.com/caronc/apprise-api)) | ⭐⭐⭐ Advanced |

---

## Alert Configuration Methods

### Method 1: UI Settings (Recommended)

1. Navigate to **Settings → Alerts** in the web UI
2. Toggle alerts **ON** and set failure threshold and cooldown
3. Enable desired providers and fill in their settings
4. Use **"Send Test Notification"** to verify configuration
5. Click **"Save Settings"** to persist to `runtime_config.json`

**Advantages:**

- No container restart required
- Test notifications before saving
- Visual validation of settings
- Supports runtime changes

### Method 2: Environment Variables

Add to your `.env` file before first container start:

```bash
# Enable alerting (set threshold > 0)
ALERT_FAILURE_THRESHOLD=3          # Send alert after 3 consecutive failures
ALERT_COOLDOWN_MINUTES=60          # Minimum 60 minutes between alerts

# Provider-specific settings (see examples below)
ALERT_WEBHOOK_URL=https://webhook.example.com/alerts
```

**Advantages:**

- Configuration as code
- Easy to version control
- Consistent across deployments

**Disadvantages:****

- Requires container restart to change settings
- No test notification feature

---

## Provider Setup Guides

### Apprise (Recommended for Multiple Recipients)

Apprise supports 100+ services including Discord, Telegram, Slack, Email, SMS, and more.

#### With Persistent Config (Recommended)

**1. Deploy Apprise API:**

```bash
docker run -d -p 8000:8000 \
  -v $(pwd)/apprise-config:/config \
  caronc/apprise-api
```

**2. Configure Hermes:**

```bash
ALERT_APPRISE_URL=https://apprise.example.com/notify/myconfig
```

**3. Manage recipients in Apprise's web UI** at `http://apprise.example.com`

#### With Stateless Mode

**1. Set Apprise URL:**

```bash
ALERT_APPRISE_URL=https://apprise.example.com
```

**2. Add service URLs in Hermes UI:** Settings → Alerts → Apprise → Service URLs:

```text
ntfys://ntfy.example.com/topic?token=tk_xxx
gotify://gotify.example.com/token
discord://webhook_id/webhook_token
tgram://bot_token/chat_id
```

See [Apprise URL documentation](https://github.com/caronc/apprise/wiki) for service-specific URL formats.

---

### ntfy

Simple pub-sub notifications using [ntfy.sh](https://ntfy.sh) or self-hosted ntfy server.

#### Public Topic (No Authentication)

```bash
ALERT_NTFY_TOPIC=hermes_alerts
ALERT_NTFY_PRIORITY=3                    # 1-5 (default: 3)
ALERT_NTFY_TAGS=warning,rotating_light   # Comma-separated emoji tags
```

Subscribe with the mobile app or web UI: `https://ntfy.sh/hermes_alerts`

#### Private Topic (With Authentication)

```bash
ALERT_NTFY_TOPIC=hermes_alerts
ALERT_NTFY_TOKEN=tk_xxxxxxxxxxxxx        # Access token from ntfy.sh
ALERT_NTFY_PRIORITY=4
```

#### Self-Hosted ntfy

```bash
ALERT_NTFY_URL=https://ntfy.yourdomain.com  # Custom ntfy server
ALERT_NTFY_TOPIC=hermes_alerts
```

**Priority Levels:**

- `1` = Min priority
- `2` = Low priority
- `3` = Default priority (default)
- `4` = High priority
- `5` = Urgent priority (bypasses Do Not Disturb)

---

### Gotify

Self-hosted push notification server. Requires deployment of Gotify server.

**1. Deploy Gotify:**

```bash
docker run -d -p 80:80 \
  -v $(pwd)/gotify-data:/app/data \
  gotify/server
```

**2. Create an Application in Gotify UI** and copy the app token

**3. Configure Hermes:**

```bash
ALERT_GOTIFY_URL=https://gotify.example.com
ALERT_GOTIFY_TOKEN=your_app_token_here
ALERT_GOTIFY_PRIORITY=5                    # 0-10 (default: 5)
```

**Priority Levels:**

- `0-3` = Low priority
- `4-7` = Normal priority
- `8-10` = High priority

---

### Webhook

Send JSON POST requests to any HTTP endpoint.

#### Setup

```bash
ALERT_WEBHOOK_URL=https://your-webhook.example.com/alerts
```

#### Payload Format

Hermes sends the following JSON payload:

```json
{
  "failure_count": 3,
  "last_error": "Connection timeout",
  "timestamp": "2026-04-29T12:00:00Z"
}
```

#### Example: Integrate with Home Assistant

```bash
ALERT_WEBHOOK_URL=http://homeassistant.local:8123/api/webhook/hermes-alert-webhook-id
```

Then create an automation in Home Assistant to handle the webhook.

#### Example: Integrate with n8n

```bash
ALERT_WEBHOOK_URL=https://n8n.example.com/webhook/hermes-alerts
```

Create a workflow in n8n triggered by the webhook to forward to multiple destinations.

---

## Alert Behavior

### Failure Detection

- Hermes tracks **consecutive** failures only
- A single successful test resets the failure counter
- Alerts trigger when `failure_count >= ALERT_FAILURE_THRESHOLD`

### Cooldown Period

- After sending an alert, Hermes waits `ALERT_COOLDOWN_MINUTES` before sending another
- Prevents notification spam during extended outages
- Cooldown applies globally across all providers

### Example Timeline

```text
Threshold = 3, Cooldown = 60 minutes

10:00 - Test fails (count: 1)
10:15 - Test fails (count: 2)
10:30 - Test fails (count: 3) → Alert sent, cooldown starts
10:45 - Test fails (count: 4) → No alert (in cooldown)
11:00 - Test fails (count: 5) → No alert (in cooldown)
11:30 - Test succeeds → Counter resets to 0, cooldown cleared
```

---

## Testing Alerts

Before deploying, verify your alert configuration:

### Via UI

1. Navigate to **Settings → Alerts**
2. Configure your provider settings
3. Click **"Send Test Notification"**
4. Check that you receive the test message
5. Click **"Save Settings"** to persist

### Via API

```bash
curl -X POST http://localhost:8080/api/alerts/test \
  -H "X-Api-Key: your-api-key-here"
```

Response:

```json
{
  "status": "success",
  "message": "Test alert sent successfully to 2 provider(s)",
  "results": {
    "webhook": true,
    "ntfy": true
  }
}
```

**Note:** Test notifications have a **10-second cooldown** to prevent spam. If you attempt multiple tests rapidly, you'll receive a "Rate limited" error response. Wait 10 seconds before sending another test notification.

---

## Troubleshooting

### No Alerts Received

1. **Check threshold:** Ensure `ALERT_FAILURE_THRESHOLD > 0`
2. **Verify provider enabled:** Check Settings → Alerts or environment variables
3. **Check cooldown:** Wait `ALERT_COOLDOWN_MINUTES` after last alert
4. **Test notification:** Use "Send Test Notification" button in UI
5. **Check logs:** Look for alert-related errors in container logs:

   ```bash
   docker logs hermes-scheduler | grep -i alert
   ```

### Partial Provider Failure

If one provider fails but others succeed, check:

- **Webhook:** Verify URL is reachable and returns 2xx status
- **Gotify:** Check server URL and app token validity
- **ntfy:** Verify topic name and authentication token
- **Apprise:** Check Apprise API is running and config ID exists

### Alert Sent Too Frequently

Increase `ALERT_COOLDOWN_MINUTES` to reduce notification frequency:

```bash
ALERT_COOLDOWN_MINUTES=120  # Wait 2 hours between alerts
```

### Alert Not Sent Despite Failures

Check `ALERT_FAILURE_THRESHOLD`:

```bash
ALERT_FAILURE_THRESHOLD=3  # Requires 3 consecutive failures
```

Lower the threshold if you want faster alerts:

```bash
ALERT_FAILURE_THRESHOLD=1  # Alert on first failure
```

---

## API Reference

### GET /api/alerts

Get current alert configuration.

**Response:**

```json
{
  "enabled": true,
  "failure_threshold": 3,
  "cooldown_minutes": 60,
  "providers": {
    "webhook": {
      "enabled": true,
      "url": "https://webhook.example.com/alerts"
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

### PUT /api/alerts

Update alert configuration. Requires `X-Api-Key` header if authentication is enabled.

**Request:**

```json
{
  "enabled": true,
  "failure_threshold": 3,
  "cooldown_minutes": 60,
  "providers": {
    "webhook": {
      "enabled": true,
      "url": "https://webhook.example.com/alerts"
    },
    "ntfy": {
      "enabled": true,
      "url": "https://ntfy.sh",
      "topic": "hermes_alerts",
      "priority": 3
    }
  }
}
```

**Response:** `200 OK` with updated configuration

### POST /api/alerts/test

Send test notification to all enabled providers. Requires `X-Api-Key` header if authentication is enabled.

**Response:**

```json
{
  "status": "success",
  "message": "Test alert sent successfully to 2 provider(s)",
  "results": {
    "webhook": true,
    "ntfy": true
  }
}
```

---

## Environment Variables Reference

Complete list of alert-related environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `ALERT_FAILURE_THRESHOLD` | `0` (disabled) | Consecutive failures before alerting |
| `ALERT_COOLDOWN_MINUTES` | `60` | Minimum minutes between alerts |
| `ALERT_WEBHOOK_URL` | *(unset)* | Webhook URL for HTTP POST |
| `ALERT_GOTIFY_URL` | *(unset)* | Gotify server URL |
| `ALERT_GOTIFY_TOKEN` | *(unset)* | Gotify application token |
| `ALERT_GOTIFY_PRIORITY` | `5` | Gotify priority (0-10) |
| `ALERT_NTFY_URL` | `https://ntfy.sh` | ntfy server URL |
| `ALERT_NTFY_TOPIC` | *(unset)* | ntfy topic name |
| `ALERT_NTFY_TOKEN` | *(unset)* | ntfy authentication token (optional) |
| `ALERT_NTFY_PRIORITY` | `3` | ntfy priority (1-5) |
| `ALERT_NTFY_TAGS` | `warning,rotating_light` | Comma-separated emoji tags |
| `ALERT_APPRISE_URL` | *(unset)* | Apprise API URL with config ID |

See [.env.example](https://github.com/fabell4/hermes/blob/main/.env.example) for detailed comments and examples.

---

## See Also

- [Getting Started](getting-started) — Deployment and configuration
- [API Reference](api-reference) — Complete API documentation
- [Security Guide](security) — SSRF protection on alert URLs
