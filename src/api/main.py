"""FastAPI entry-point for the Hermes REST API.

Run with:
    uvicorn src.api.main:app --port 8080 --reload
"""

import time
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.routes import config, results, trigger
from src import runtime_config as rc

_START_TIME = time.time()

app = FastAPI(
    title="Hermes API",
    description="REST interface for the Hermes speed-monitor.",
    version="0.1.0",
)

# Allow the Vite dev server (localhost:5173) and any same-origin requests.
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
    )
