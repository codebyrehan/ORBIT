"""Production application entrypoint with the complete ORBIT product router."""
from __future__ import annotations

from fastapi import FastAPI

from orbit.api.platform import router as product_router
from orbit.api.server import create_app

app: FastAPI = create_app()
app.include_router(product_router)

@app.get("/control", include_in_schema=False)
async def control_center() -> dict[str, object]:
    return {"service":"ORBIT Control Center","status":"ok","api":"/v1","docs":"/docs","modules":["models","projects","knowledge","agents","tools","mcp","media","security","packaging"]}
