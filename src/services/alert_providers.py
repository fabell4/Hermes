"""Alert providers — send notifications via different channels (webhook, Gotify, ntfy, Apprise)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AlertProvider(ABC):
    """Base class for alert notification providers."""

    @abstractmethod
    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """
        Send an alert notification.

        Args:
            failure_count: Number of consecutive failures
            last_error: Error message from the last failed attempt
            timestamp: When the last failure occurred
        """


class WebhookProvider(AlertProvider):
    """Sends alerts via HTTP POST to a configured webhook URL."""

    def __init__(self, url: str, timeout: int = 10) -> None:
        """
        Initialize webhook provider.

        Args:
            url: The webhook URL to POST to
            timeout: Request timeout in seconds
        """
        if not url:
            raise ValueError("Webhook URL cannot be empty")
        self.url = url
        self.timeout = timeout

    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """Send alert via webhook POST request."""
        payload = {
            "type": "speedtest_failure",
            "consecutive_failures": failure_count,
            "error": last_error,
            "timestamp": timestamp.isoformat(),
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.info(
                "Webhook alert sent to %s (status: %d)", self.url, response.status_code
            )
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send webhook alert to %s: %s", self.url, e)
            raise


class GotifyProvider(AlertProvider):
    """Sends alerts via Gotify push notification service."""

    def __init__(
        self, url: str, token: str, priority: int = 5, timeout: int = 10
    ) -> None:
        """
        Initialize Gotify provider.

        Args:
            url: Gotify server URL (e.g., https://gotify.example.com)
            token: Application token for authentication
            priority: Message priority (0-10, default 5)
            timeout: Request timeout in seconds
        """
        if not url:
            raise ValueError("Gotify URL cannot be empty")
        if not token:
            raise ValueError("Gotify token cannot be empty")

        self.url = url.rstrip("/")
        self.token = token
        self.priority = max(0, min(10, priority))  # Clamp to 0-10
        self.timeout = timeout

    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """Send alert via Gotify push notification."""
        endpoint = f"{self.url}/message"
        title = f"⚠️ Speedtest Failure ({failure_count} consecutive)"
        message = f"**Error:** {last_error}\n\n**Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

        payload = {
            "title": title,
            "message": message,
            "priority": self.priority,
            "extras": {
                "client::display": {"contentType": "text/markdown"},
                "hermes::failure_count": failure_count,
            },
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                params={"token": self.token},
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(
                "Gotify alert sent to %s (status: %d)", self.url, response.status_code
            )
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send Gotify alert to %s: %s", self.url, e)
            raise


class NtfyProvider(AlertProvider):
    """Sends alerts via ntfy.sh push notification service."""

    def __init__(
        self,
        url: str = "https://ntfy.sh",
        topic: str = "",
        token: str | None = None,
        priority: int = 3,
        tags: list[str] | None = None,
        timeout: int = 10,
    ) -> None:
        """
        Initialize ntfy provider.

        Args:
            url: ntfy server URL (default: https://ntfy.sh)
            topic: Topic name to publish to
            token: Optional access token for authentication
            priority: Message priority (1-5, default 3)
            tags: List of tags/emojis for the notification
            timeout: Request timeout in seconds
        """
        if not topic:
            raise ValueError("ntfy topic cannot be empty")

        self.url = url.rstrip("/")
        self.topic = topic
        self.token = token
        self.priority = max(1, min(5, priority))  # Clamp to 1-5
        self.tags = tags or ["warning", "rotating_light"]
        self.timeout = timeout

    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """Send alert via ntfy push notification."""
        endpoint = f"{self.url}/{self.topic}"
        title = f"Speedtest Failure ({failure_count} consecutive)"
        message = f"{last_error}\n\nTime: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

        headers = {
            "Title": title,
            "Priority": str(self.priority),
            "Tags": ",".join(self.tags),
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = requests.post(
                endpoint,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(
                "ntfy alert sent to %s/%s (status: %d)",
                self.url,
                self.topic,
                response.status_code,
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to send ntfy alert to %s/%s: %s", self.url, self.topic, e
            )
            raise


class AppriseProvider(AlertProvider):
    """Sends alerts via Apprise API service (separate container)."""

    def __init__(self, url: str, timeout: int = 10) -> None:
        """
        Initialize Apprise provider.

        Args:
            url: Apprise API URL (e.g., http://apprise:8000/notify)
            timeout: Request timeout in seconds

        Raises:
            ValueError: If URL is empty
        """
        if not url:
            raise ValueError("Apprise API URL cannot be empty")

        self.url = url.rstrip("/")
        self.timeout = timeout

    def send_alert(
        self,
        failure_count: int,
        last_error: str,
        timestamp: datetime,
    ) -> None:
        """Send alert via Apprise API POST request.

        URL can be:
        - Base URL (e.g., http://apprise:8000) - will append /notify
        - Full endpoint (e.g., http://apprise:8000/notify/myconfig) - used as-is
        """
        # If URL already contains /notify, use it as-is, otherwise append /notify
        if "/notify" in self.url:
            endpoint = self.url
        else:
            endpoint = f"{self.url}/notify"

        title = f"⚠️ Speedtest Failure ({failure_count} consecutive)"
        body = f"{last_error}\n\nTime: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

        payload = {
            "title": title,
            "body": body,
            "type": "warning",
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.info(
                "Apprise alert sent to %s (status: %d)", self.url, response.status_code
            )
        except requests.exceptions.RequestException as e:
            logger.error("Failed to send Apprise alert to %s: %s", self.url, e)
            raise


def create_provider(provider_type: str, config: dict[str, Any]) -> AlertProvider:
    """
    Factory function to create an alert provider based on type.

    Args:
        provider_type: Type of provider ("webhook", "gotify", "ntfy", "apprise")
        config: Provider-specific configuration dictionary

    Returns:
        Configured AlertProvider instance

    Raises:
        ValueError: If provider type is unknown or config is invalid
    """
    provider_type = provider_type.lower()

    if provider_type == "webhook":
        return WebhookProvider(
            url=config["url"],
            timeout=config.get("timeout", 10),
        )
    elif provider_type == "gotify":
        return GotifyProvider(
            url=config["url"],
            token=config["token"],
            priority=config.get("priority", 5),
            timeout=config.get("timeout", 10),
        )
    elif provider_type == "ntfy":
        return NtfyProvider(
            url=config.get("url", "https://ntfy.sh"),
            topic=config["topic"],
            token=config.get("token"),
            priority=config.get("priority", 3),
            tags=config.get("tags"),
            timeout=config.get("timeout", 10),
        )
    elif provider_type == "apprise":
        return AppriseProvider(
            url=config["url"],
            timeout=config.get("timeout", 10),
        )
    else:
        raise ValueError(f"Unknown alert provider type: {provider_type}")
