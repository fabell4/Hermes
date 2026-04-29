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
