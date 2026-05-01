"""Tests for src/services/alert_providers.py."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from src.services.alert_providers import (
    WebhookProvider,
    GotifyProvider,
    NtfyProvider,
    AppriseProvider,
    create_provider,
)


# ---------------------------------------------------------------------------
# WebhookProvider
# ---------------------------------------------------------------------------


def test_webhook_provider_raises_on_empty_url():
    with pytest.raises(ValueError, match="cannot be empty"):
        WebhookProvider(url="")


@patch("src.services.alert_providers.requests.post")
def test_webhook_provider_sends_json_post(mock_post):
    """Webhook provider POSTs JSON payload."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    provider = WebhookProvider(url="https://webhook.example.com")
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    provider.send_alert(
        failure_count=3,
        last_error="Speedtest failed",
        timestamp=timestamp,
    )

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args.args[0] == "https://webhook.example.com"
    assert call_args.kwargs["json"]["consecutive_failures"] == 3
    assert call_args.kwargs["json"]["error"] == "Speedtest failed"
    assert call_args.kwargs["headers"]["Content-Type"] == "application/json"


@patch("src.services.alert_providers.requests.post")
def test_webhook_provider_raises_on_request_error(mock_post):
    """Webhook provider raises on HTTP error."""
    import requests

    mock_post.side_effect = requests.exceptions.RequestException("Network error")

    provider = WebhookProvider(url="https://webhook.example.com")
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(requests.exceptions.RequestException):
        provider.send_alert(3, "Speedtest failed", timestamp)


# ---------------------------------------------------------------------------
# GotifyProvider
# ---------------------------------------------------------------------------


def test_gotify_provider_raises_on_empty_url():
    with pytest.raises(ValueError, match="cannot be empty"):
        GotifyProvider(url="", token="token")


def test_gotify_provider_raises_on_empty_token():
    with pytest.raises(ValueError, match="cannot be empty"):
        GotifyProvider(url="https://gotify.example.com", token="")


@patch("src.services.alert_providers.requests.post")
def test_gotify_provider_sends_message(mock_post):
    """Gotify provider sends formatted push notification."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    provider = GotifyProvider(
        url="https://gotify.example.com",
        token="app-token",
        priority=8,
    )
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    provider.send_alert(
        failure_count=5,
        last_error="Network timeout",
        timestamp=timestamp,
    )

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "gotify.example.com/message" in call_args.args[0]
    assert call_args.kwargs["params"]["token"] == "app-token"
    assert call_args.kwargs["json"]["priority"] == 8
    assert "5 consecutive" in call_args.kwargs["json"]["title"]


def test_gotify_provider_clamps_priority():
    """Priority is clamped to valid range 0-10."""
    provider = GotifyProvider(
        url="https://gotify.example.com",
        token="token",
        priority=15,  # Above max
    )
    assert provider.priority == 10

    provider = GotifyProvider(
        url="https://gotify.example.com",
        token="token",
        priority=-5,  # Below min
    )
    assert provider.priority == 0


# ---------------------------------------------------------------------------
# NtfyProvider
# ---------------------------------------------------------------------------


def test_ntfy_provider_raises_on_empty_topic():
    with pytest.raises(ValueError, match="cannot be empty"):
        NtfyProvider(topic="")


@patch("src.services.alert_providers.requests.post")
def test_ntfy_provider_sends_notification(mock_post):
    """ntfy provider sends notification to topic."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    provider = NtfyProvider(
        url="https://ntfy.sh",
        topic="hermes-alerts",
        priority=4,
        tags=["warning", "alert"],
    )
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    provider.send_alert(
        failure_count=2,
        last_error="Connection refused",
        timestamp=timestamp,
    )

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "ntfy.sh/hermes-alerts" in call_args.args[0]
    assert call_args.kwargs["headers"]["Priority"] == "4"
    assert call_args.kwargs["headers"]["Tags"] == "warning,alert"
    assert b"Connection refused" in call_args.kwargs["data"]


def test_ntfy_provider_clamps_priority():
    """Priority is clamped to valid range 1-5."""
    provider = NtfyProvider(topic="test", priority=10)  # Above max
    assert provider.priority == 5

    provider = NtfyProvider(topic="test", priority=0)  # Below min
    assert provider.priority == 1


def test_ntfy_provider_default_url():
    """Default URL is ntfy.sh if not provided."""
    provider = NtfyProvider(topic="test")
    assert provider.url == "https://ntfy.sh"


# ---------------------------------------------------------------------------
# AppriseProvider
# ---------------------------------------------------------------------------


def test_apprise_provider_raises_on_empty_url():
    with pytest.raises(ValueError, match="cannot be empty"):
        AppriseProvider(url="")


@patch("src.services.alert_providers.requests.post")
def test_apprise_provider_sends_notification(mock_post):
    """AppriseProvider sends notification via HTTP POST."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response

    provider = AppriseProvider(url="http://apprise:8000")  # NOSONAR
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    provider.send_alert(
        failure_count=3,
        last_error="Connection timeout",
        timestamp=timestamp,
    )

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args.args[0] == "http://apprise:8000/notify"  # NOSONAR
    assert "3 consecutive" in call_args.kwargs["json"]["title"]
    assert "Connection timeout" in call_args.kwargs["json"]["body"]
    assert call_args.kwargs["json"]["type"] == "warning"


@patch("src.services.alert_providers.requests.post")
def test_apprise_provider_raises_on_request_error(mock_post):
    """AppriseProvider raises on HTTP error."""
    import requests

    mock_post.side_effect = requests.exceptions.RequestException("Service unavailable")

    provider = AppriseProvider(url="http://apprise:8000")  # NOSONAR
    timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(requests.exceptions.RequestException):
        provider.send_alert(3, "Error", timestamp)


# ---------------------------------------------------------------------------
# create_provider()
# ---------------------------------------------------------------------------


def test_create_provider_webhook():
    """Factory creates webhook provider."""
    config = {"url": "https://webhook.example.com"}
    provider = create_provider("webhook", config)
    assert isinstance(provider, WebhookProvider)
    assert provider.url == "https://webhook.example.com"


def test_create_provider_gotify():
    """Factory creates Gotify provider."""
    config = {
        "url": "https://gotify.example.com",
        "token": "app-token",
        "priority": 7,
    }
    provider = create_provider("gotify", config)
    assert isinstance(provider, GotifyProvider)
    assert provider.url == "https://gotify.example.com"
    assert provider.token == "app-token"
    assert provider.priority == 7


def test_create_provider_ntfy():
    """Factory creates ntfy provider."""
    config = {
        "url": "https://ntfy.example.com",
        "topic": "alerts",
        "priority": 4,
        "tags": ["warning"],
    }
    provider = create_provider("ntfy", config)
    assert isinstance(provider, NtfyProvider)
    assert provider.url == "https://ntfy.example.com"
    assert provider.topic == "alerts"
    assert provider.priority == 4
    assert provider.tags == ["warning"]


def test_create_provider_apprise():
    """Factory creates apprise provider."""
    config = {
        "url": "http://apprise:8000",  # NOSONAR
    }
    provider = create_provider("apprise", config)
    assert isinstance(provider, AppriseProvider)
    assert provider.url == "http://apprise:8000"  # NOSONAR


def test_create_provider_unknown_type():
    """Factory raises ValueError for unknown provider type."""
    with pytest.raises(ValueError, match="Unknown alert provider"):
        create_provider("unknown", {})


def test_create_provider_case_insensitive():
    """Factory accepts case-insensitive provider type."""
    config = {"url": "https://webhook.example.com"}
    provider = create_provider("WEBHOOK", config)
    assert isinstance(provider, WebhookProvider)


# ---------------------------------------------------------------------------
# _validate_http_url — error paths
# ---------------------------------------------------------------------------


def test_validate_http_url_non_http_scheme():
    """Providers reject URLs with non-HTTP schemes."""
    with pytest.raises(ValueError, match="must use http or https"):
        WebhookProvider(url="ftp://example.com/hook")


def test_validate_http_url_missing_hostname():
    """Providers reject URLs with no hostname."""
    with pytest.raises(ValueError, match="must include a hostname"):
        WebhookProvider(url="http://")


# ---------------------------------------------------------------------------
# Provider timeout validation
# ---------------------------------------------------------------------------


def test_webhook_provider_rejects_non_positive_timeout():
    """WebhookProvider raises on timeout <= 0."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        WebhookProvider(url="https://example.com", timeout=0)


def test_gotify_provider_rejects_non_positive_timeout():
    """GotifyProvider raises on timeout <= 0."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        GotifyProvider(url="https://gotify.example.com", token="tok", timeout=-1)


def test_ntfy_provider_rejects_non_positive_timeout():
    """NtfyProvider raises on timeout <= 0."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        NtfyProvider(topic="alerts", timeout=0)


# ---------------------------------------------------------------------------
# NtfyProvider — auth token header and error raise
# ---------------------------------------------------------------------------


@patch("src.services.alert_providers.requests.post")
def test_ntfy_provider_sends_with_auth_token(mock_post):
    """NtfyProvider adds Authorization header when token is provided."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    provider = NtfyProvider(
        url="https://ntfy.example.com",
        topic="alerts",
        token="mytoken123",
    )
    provider.send_alert(
        failure_count=2,
        last_error="Connection refused",
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    call_args = mock_post.call_args
    assert "Authorization" in call_args.kwargs["headers"]
    assert call_args.kwargs["headers"]["Authorization"] == "Bearer mytoken123"


@patch("src.services.alert_providers.requests.post")
def test_ntfy_provider_raises_on_request_error(mock_post):
    """NtfyProvider re-raises RequestException after logging."""
    import requests as req

    mock_post.side_effect = req.exceptions.RequestException("timeout")

    provider = NtfyProvider(topic="alerts")
    with pytest.raises(req.exceptions.RequestException):
        provider.send_alert(
            failure_count=1,
            last_error="err",
            timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        )


# ---------------------------------------------------------------------------
# AppriseProvider — stateless mode and /notify URL handling
# ---------------------------------------------------------------------------


@patch("src.services.alert_providers.requests.post")
def test_apprise_provider_stateless_mode_includes_urls(mock_post):
    """AppriseProvider includes 'urls' key in payload for stateless mode."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response

    provider = AppriseProvider(
        url="http://apprise:8000",  # NOSONAR
        urls=["ntfy://topic", "gotify://server/token"],
    )
    provider.send_alert(
        failure_count=1,
        last_error="error",
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    payload = mock_post.call_args.kwargs["json"]
    assert "urls" in payload
    assert "ntfy://topic" in payload["urls"]


@patch("src.services.alert_providers.requests.post")
def test_apprise_provider_url_with_notify_uses_as_is(mock_post):
    """AppriseProvider uses URL as-is when it already contains /notify."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response

    provider = AppriseProvider(url="http://apprise:8000/notify/myconfig")  # NOSONAR
    provider.send_alert(
        failure_count=1,
        last_error="error",
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    called_url = mock_post.call_args.args[0]
    # URL should not have /notify appended again
    assert called_url == "http://apprise:8000/notify/myconfig"  # NOSONAR


@patch("src.services.alert_providers.requests.post")
def test_apprise_provider_reraises_request_exception_with_logging(mock_post):
    """AppriseProvider re-raises RequestException after logging."""
    import requests as req

    mock_post.side_effect = req.exceptions.RequestException("connection refused")

    provider = AppriseProvider(url="http://apprise:8000")  # NOSONAR
    with pytest.raises(req.exceptions.RequestException):
        provider.send_alert(
            failure_count=2,
            last_error="error",
            timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
