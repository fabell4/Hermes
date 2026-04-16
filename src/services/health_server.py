"""health_server.py — lightweight HTTP server exposing a /health endpoint."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable

logger = logging.getLogger(__name__)  # type: ignore


class _HealthHandler(BaseHTTPRequestHandler):
    """Handles GET /health requests."""

    # Injected by HealthServer before the server starts.
    get_status: Callable[[], dict]

    def do_GET(self) -> None:  # noqa: N802  # pylint: disable=invalid-name
        """Handle GET requests; only /health is served."""
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        payload = self.get_status()
        body = json.dumps(payload, default=str).encode()
        status_code = 200 if payload.get("status") == "ok" else 503
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # type: ignore[override]
        logger.debug("health request: %s", args)


class HealthServer:
    """
    Runs a daemon HTTP server in a background thread.

    The *get_status* callable is invoked on every request and must return a
    plain dict that will be serialised to JSON.  The HTTP status code is 200
    when ``status == "ok"`` and 503 otherwise.
    """

    def __init__(self, port: int, get_status: Callable[[], dict]) -> None:
        self._port = port

        # Bind the status callback onto the handler class via a subclass so
        # that multiple HealthServer instances (e.g. in tests) don't share state.
        handler_cls = type(
            "_BoundHealthHandler",
            (_HealthHandler,),
            {"get_status": staticmethod(get_status)},
        )
        self._server = HTTPServer(("", port), handler_cls)

    def start(self) -> None:
        """Start serving in a background daemon thread."""
        thread = threading.Thread(
            target=self._server.serve_forever,
            name="health-server",
            daemon=True,
        )
        thread.start()
        logger.info("Health endpoint started on port %d — GET /health", self._port)

    def stop(self) -> None:
        """Shut down the server (blocks until the current request finishes)."""
        self._server.shutdown()
