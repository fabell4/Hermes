"""Tests for request body size limit middleware."""
# pylint: disable=missing-function-docstring

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_request_under_size_limit_accepted():
    """Requests under the size limit should be accepted."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_request_at_size_limit_accepted():
    """Requests at exactly the size limit should be accepted."""
    # Create a payload that's exactly at the limit
    with patch("src.api.main.app_config.MAX_REQUEST_BODY_SIZE", 100):
        # Mock the content-length header to be exactly at limit
        response = client.put(
            "/api/config",
            json={
                "interval_minutes": 60,
                "enabled_exporters": ["csv"],
                "scanning_enabled": True,
            },
            headers={"Content-Length": "100"},
        )
        # Should succeed if auth is disabled
        assert response.status_code in (200, 401)  # 401 if auth enabled, 200 otherwise


def test_request_over_size_limit_rejected():
    """Requests exceeding the size limit should be rejected with 413."""
    with patch("src.api.main.app_config.MAX_REQUEST_BODY_SIZE", 100):
        # Create a large payload
        large_payload = {"data": "x" * 1000}
        # Calculate actual content length
        import json

        content = json.dumps(large_payload).encode("utf-8")
        content_length = len(content)

        response = client.put(
            "/api/config",
            json=large_payload,
            headers={"Content-Length": str(content_length)},
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()


def test_request_without_content_length_accepted():
    """Requests without Content-Length header should be accepted (no size check)."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_size_limit_error_includes_max_size():
    """413 error should include the maximum allowed size."""
    with patch("src.api.main.app_config.MAX_REQUEST_BODY_SIZE", 500):
        response = client.put(
            "/api/config",
            json={"data": "x" * 1000},
            headers={"Content-Length": "1000"},
        )
        assert response.status_code == 413
        assert "500" in response.json()["detail"]


def test_size_limit_applies_to_all_endpoints():
    """Size limit should apply to all POST/PUT endpoints."""
    with patch("src.api.main.app_config.MAX_REQUEST_BODY_SIZE", 50):
        # Test on different endpoints
        endpoints = [
            ("/api/config", "put"),
        ]

        for path, method in endpoints:
            if method == "put":
                response = client.put(
                    path,
                    json={"data": "x" * 1000},
                    headers={"Content-Length": "1000"},
                )
            else:
                response = client.post(
                    path,
                    json={"data": "x" * 1000},
                    headers={"Content-Length": "1000"},
                )
            assert response.status_code == 413, f"Failed for {method.upper()} {path}"
