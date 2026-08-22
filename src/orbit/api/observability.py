"""API-facing observability endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from orbit.observability import RuntimeMetrics

router = APIRouter(tags=["observability"])


def metrics_for(request: Request) -> RuntimeMetrics:
    metrics = getattr(request.app.state, "orbit_metrics", None)
    if metrics is None:
        metrics = RuntimeMetrics()
        request.app.state.orbit_metrics = metrics
    return metrics


@router.get("/v1/metrics")
async def metrics(request: Request) -> dict[str, float | int]:
    """Return process-local inference metrics."""
    return metrics_for(request).snapshot()
