"""Production application entrypoint with the complete ORBIT product router."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orbit.api.platform import router as product_router
from orbit.api.server import create_app

app: FastAPI = create_app()
app.include_router(product_router)

@app.exception_handler(PermissionError)
async def permission_error(request: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.get("/control", include_in_schema=False)
async def control_center() -> dict[str, object]:
    return {"service":"ORBIT Control Center","status":"ok","api":"/v1","docs":"/docs","modules":["models","projects","knowledge","agents","tools","mcp","media","security","packaging"]}
