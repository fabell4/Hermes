"""GET /api/diagnostics — latest quality score and SLA status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src import shared_state

router = APIRouter(tags=["diagnostics"])


class SLAStatusSchema(BaseModel):
    """Per-dimension SLA pass/fail flags for the latest run."""

    download_ok: bool | None = None
    upload_ok: bool | None = None
    ping_ok: bool | None = None
    packet_loss_ok: bool | None = None
    overall_ok: bool


class DiagnosticsResponse(BaseModel):
    """Response schema for GET /api/diagnostics."""

    quality_score: float | None = None
    sla_ok: bool | None = None
    sla_detail: SLAStatusSchema | None = None
    packet_loss_pct: float | None = None
    message: str


@router.get("/diagnostics")
def get_diagnostics() -> DiagnosticsResponse:
    """Return the latest connection quality score and SLA status.

    Returns 503-style message when no run has completed yet.
    """
    data: dict[str, Any] | None = shared_state.get_last_diagnostics()

    if data is None:
        return DiagnosticsResponse(
            message="No run completed yet — diagnostics will appear after the first test."
        )

    sla_detail: SLAStatusSchema | None = None
    if "sla_detail" in data and data["sla_detail"] is not None:
        sla_detail = SLAStatusSchema(**data["sla_detail"])

    return DiagnosticsResponse(
        quality_score=data.get("quality_score"),
        sla_ok=data.get("sla_ok"),
        sla_detail=sla_detail,
        packet_loss_pct=data.get("packet_loss_pct"),
        message="ok",
    )
