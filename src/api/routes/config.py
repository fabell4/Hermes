"""GET /api/config and PUT /api/config — runtime configuration via the UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src import config as app_config
from src import runtime_config
from src.api.auth import require_api_key

router = APIRouter(tags=["config"])

VALID_EXPORTERS = frozenset({"csv", "sqlite", "prometheus", "loki"})


class RuntimeConfigSchema(BaseModel):
    """Request/response schema for the runtime configuration endpoints."""

    interval_minutes: int = Field(ge=5, le=1440)
    enabled_exporters: list[str]
    scanning_enabled: bool


@router.get("/config")
def get_config() -> RuntimeConfigSchema:
    """Return the current runtime configuration."""
    return RuntimeConfigSchema(
        interval_minutes=runtime_config.get_interval_minutes(
            app_config.SPEEDTEST_INTERVAL_MINUTES
        ),
        enabled_exporters=runtime_config.get_enabled_exporters(
            app_config.ENABLED_EXPORTERS
        ),
        scanning_enabled=not runtime_config.load().get("scanning_disabled", False),
    )


@router.put(
    "/config",
    dependencies=[Depends(require_api_key)],
    responses={422: {"description": "One or more unknown exporter names supplied."}},
)
def update_config(body: RuntimeConfigSchema) -> RuntimeConfigSchema:
    """Persist updated runtime configuration."""
    unknown = [e for e in body.enabled_exporters if e not in VALID_EXPORTERS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown exporters: {unknown}",
        )

    runtime_config.save(
        {
            "interval_minutes": body.interval_minutes,
            "enabled_exporters": body.enabled_exporters,
            "scanning_disabled": not body.scanning_enabled,
        }
    )
    return get_config()
