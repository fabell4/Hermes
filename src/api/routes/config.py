"""GET /api/config and PUT /api/config — runtime configuration via the UI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src import config as app_config
from src import runtime_config
from src.api.auth import require_api_key

router = APIRouter(tags=["config"])

VALID_EXPORTERS = frozenset({"csv", "sqlite", "prometheus", "loki"})


class TestWindowSchema(BaseModel):
    """Configuration for restricting automated tests to specific hours (UTC)."""

    enabled: bool
    start_hour: int = Field(
        ge=0, le=23, description="Inclusive start hour (UTC, 0–23)."
    )
    end_hour: int = Field(ge=1, le=24, description="Exclusive end hour (UTC, 1–24).")


class RuntimeConfigSchema(BaseModel):
    """Request/response schema for the runtime configuration endpoints."""

    interval_minutes: int = Field(ge=5, le=1440)
    enabled_exporters: list[str]
    scanning_enabled: bool
    test_window: TestWindowSchema


@router.get("/config")
def get_config() -> RuntimeConfigSchema:
    """Return the current runtime configuration."""
    tw = runtime_config.get_test_window()
    return RuntimeConfigSchema(
        interval_minutes=runtime_config.get_interval_minutes(
            app_config.SPEEDTEST_INTERVAL_MINUTES
        ),
        enabled_exporters=runtime_config.get_enabled_exporters(
            app_config.ENABLED_EXPORTERS
        ),
        scanning_enabled=not runtime_config.load().get("scanning_disabled", False),
        test_window=TestWindowSchema(
            enabled=tw["enabled"],
            start_hour=tw["start_hour"],
            end_hour=tw["end_hour"],
        ),
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
            "test_window": body.test_window.model_dump(),
        }
    )
    return get_config()
