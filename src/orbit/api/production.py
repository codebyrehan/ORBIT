"""Production entrypoint with a human-friendly service landing route."""

from __future__ import annotations

from fastapi import FastAPI

from orbit.api.server import create_app


app: FastAPI = create_app()


@app.get("/", include_in_schema=False)
async def service_root() -> dict[str, object]:
    """Return service metadata instead of FastAPI's default 404 at the public URL."""
    return {
        "service": "ORBIT API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "api": "/v1",
    }
