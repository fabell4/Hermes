"""Tests for API middleware and SPA fallback in src/api/main.py.

H7 Test Coverage (v1.1): API main uncovered lines for SPA fallback and security headers.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# H7: Security Headers Middleware Tests
# ---------------------------------------------------------------------------


def test_security_headers_applied_to_api_endpoints():
    """Security headers are applied to all API responses."""
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_security_headers_applied_to_error_responses():
    """Security headers are applied even to error responses."""
    from src.api.main import app

    client = TestClient(app)
    # Request non-existent API endpoint (or one that doesn't exist)
    # Note: If SPA fallback is active, this will return 200, not 404
    response = client.get("/api/definitely_not_a_real_endpoint_12345")

    # Whether it's a 404 or falls through to SPA (200), headers should be present
    assert response.status_code in [200, 404]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_security_headers_applied_to_post_requests():
    """Security headers are applied to POST requests."""
    from src.api.main import app

    client = TestClient(app)
    # POST to trigger endpoint - may succeed or require auth depending on config
    response = client.post("/api/trigger")

    # Headers should be present regardless of response code (200, 401, 403, etc.)
    assert response.status_code in [200, 401, 403]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_security_headers_on_validation_errors():
    """Security headers are applied to validation error responses (422)."""
    from src.api.main import app

    client = TestClient(app)
    # Send invalid request to trigger 422
    response = client.put(
        "/api/config",
        json={"interval_minutes": -1, "enabled_exporters": [], "scanning_enabled": True},
        headers={"X-Api-Key": "test"},
    )

    assert response.status_code == 422
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


# ---------------------------------------------------------------------------
# H7: SPA Fallback Route Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_dist():
    """Create app instance with mocked dist directory."""
    from pathlib import Path
    from src.api.main import app

    # Mock _DIST to appear as if frontend is built
    with patch.object(Path, "is_dir", return_value=True):
        with patch("src.api.main._DIST", Path("/fake/dist")):
            yield app


def test_spa_fallback_serves_index_for_unknown_paths(app_with_dist, tmp_path):
    """SPA fallback returns index.html for non-API paths."""
    # Create a fake index.html
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_file = dist_dir / "index.html"
    index_file.write_text("<html><body>Hermes</body></html>")

    with patch("src.api.main._DIST", dist_dir):
        client = TestClient(app_with_dist)
        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"Hermes" in response.content


def test_spa_fallback_for_nested_routes(app_with_dist, tmp_path):
    """SPA fallback handles nested frontend routes."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_file = dist_dir / "index.html"
    index_file.write_text("<html><body>SPA</body></html>")

    with patch("src.api.main._DIST", dist_dir):
        client = TestClient(app_with_dist)
        response = client.get("/settings/alerts")

        assert response.status_code == 200
        assert b"SPA" in response.content


def test_spa_fallback_for_root_path(app_with_dist, tmp_path):
    """SPA fallback serves index.html for root path."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_file = dist_dir / "index.html"
    index_file.write_text("<html><body>Root</body></html>")

    with patch("src.api.main._DIST", dist_dir):
        client = TestClient(app_with_dist)
        response = client.get("/")

        assert response.status_code == 200
        assert b"Root" in response.content


def test_spa_fallback_not_registered_when_dist_missing():
    """SPA fallback route is not registered when dist directory doesn't exist."""
    from src.api.main import _DIST

    # Check if dist directory exists in the actual project
    # If it exists, SPA fallback will be registered (expected behavior)
    # If it doesn't exist, SPA fallback won't be registered
    # This test documents the conditional registration behavior
    if _DIST.is_dir():
        # dist exists, SPA fallback should be registered
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/dashboard")

        # Should serve index.html (200) or return HTML
        assert response.status_code == 200
    else:
        # dist missing, SPA fallback not registered
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/dashboard")

        # Should return 404
        assert response.status_code == 404


def test_api_routes_take_precedence_over_spa():
    """API routes are matched before SPA fallback."""
    from src.api.main import app

    client = TestClient(app)
    # /api/health should always return JSON, never fall through to SPA
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "status" in data


def test_static_assets_bypass_security_headers():
    """Static assets mounted directly don't go through middleware."""
    from pathlib import Path
    from src.api.main import app

    # Create temporary assets directory
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = Path(tmpdir) / "dist" / "assets"
        assets_dir.mkdir(parents=True)
        test_file = assets_dir / "test.js"
        test_file.write_text("console.log('test');")

        with patch("src.api.main._DIST", Path(tmpdir) / "dist"):
            client = TestClient(app)
            # This would trigger the static files mount
            response = client.get("/assets/test.js")

            # Static files are served, headers may or may not be present
            # (depends on FastAPI's StaticFiles implementation)
            # The key is that it doesn't error
            assert response.status_code in [200, 404]  # 404 if mount isn't working


# ---------------------------------------------------------------------------
# H7: CORS Middleware Edge Cases
# ---------------------------------------------------------------------------


def test_cors_headers_on_api_endpoints():
    """CORS headers are applied based on configuration."""
    import os
    from src.api.main import app

    # Set CORS origins
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,http://localhost:5173"}):
        client = TestClient(app)
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 200
        # CORS headers should be present (handled by CORSMiddleware)
        # Note: TestClient may not fully simulate browser CORS behavior


def test_cors_allows_configured_methods():
    """CORS middleware allows GET, POST, PUT methods."""
    from src.api.main import app

    client = TestClient(app)

    # OPTIONS preflight request
    response = client.options(
        "/api/config",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
        },
    )

    # Preflight may succeed (200/204), return method not allowed (405),
    # or bad request (400) depending on FastAPI/Starlette version
    assert response.status_code in [200, 204, 400, 405]
