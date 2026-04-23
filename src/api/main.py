"""FastAPI entry-point for the Hermes REST API.

Run with:
    uvicorn src.api.main:app --port 8080 --reload
"""

import logging
import os
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse

from src.api.routes import config, results, trigger
from src import runtime_config as rc

logger = logging.getLogger(__name__)

_START_TIME = time.time()

# Path to the pre-built Vite output — present in Docker, absent in dev.
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

app = FastAPI(
    title="Hermes API",
    description="REST interface for the Hermes speed-monitor.",
    version="0.1.0",
)

# Allow the Vite dev server (localhost:5173) and any same-origin requests.
class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response


app.add_middleware(_SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(results.router, prefix="/api")
app.include_router(trigger.router, prefix="/api")
app.include_router(config.router, prefix="/api")


class HealthResponse(BaseModel):
    """Response schema for the /api/health endpoint."""

    status: Literal["ok", "degraded"]
    scheduler_running: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    uptime_seconds: float
    version: str


@app.get("/api/health", tags=["health"])
def health() -> HealthResponse:
    """Return scheduler and application health status."""
    data = rc.load()
    return HealthResponse(
        status="ok",
        scheduler_running=not data.get("scanning_disabled", False),
        last_run=data.get("last_run_at"),
        next_run=data.get("next_run_at"),
        uptime_seconds=round(time.time() - _START_TIME, 1),
        version=os.environ.get("APP_VERSION", "dev"),
    )


# ---------------------------------------------------------------------------
# SPA static file serving — only active when the Vite dist folder exists
# (i.e. in the Docker image). In development the Vite dev server handles this.
# API routes registered above take precedence; this catch-all serves the SPA.
# ---------------------------------------------------------------------------
if _DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """Return index.html for all non-API paths to support client-side routing."""
        logger.debug("SPA fallback: /%s", full_path)
        return FileResponse(str(_DIST / "index.html"))
