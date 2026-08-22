"""FastAPI application exposing ORBIT's stable control-plane surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from orbit.api.observability import metrics_for
from orbit.api.runtime_control import RuntimeExecutionError, RuntimeExecutor
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.health import HealthStatus
from orbit.core.model_artifacts import ModelArtifactError, ModelArtifactManager
from orbit.core.model_installer import ModelInstallError, ModelInstaller
from orbit.core.models import ModelModality, ModelSpec
from orbit.core.runtime import GenerationRequest
from orbit.observability import RequestTrace, RuntimeMetrics, configure_logging


class ChatMessage(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class ModelVerifyRequest(BaseModel):
    path: str = Field(min_length=1)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class ModelRegisterRequest(BaseModel):
    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    modality: ModelModality = ModelModality.TEXT
    size_bytes: int | None = Field(default=None, ge=0)
    min_memory_bytes: int | None = Field(default=None, ge=0)
    capabilities: list[str] = Field(default_factory=list)
    runtimes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ModelInstallRequest(BaseModel):
    source_path: str = Field(min_length=1)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


@dataclass(slots=True)
class ApiContext:
    app: OrbitApp


def _context(request: Request) -> ApiContext:
    context = request.app.state.orbit_context
    if not isinstance(context, ApiContext):
        raise TypeError("ORBIT API context is unavailable")
    if context.app.state.value not in {"ready", "starting"}:
        context.app.start()
    return context


def create_app(app: OrbitApp | None = None) -> FastAPI:
    configure_logging()
    orbit = app or OrbitApp(OrbitConfig.default())
    api = FastAPI(title="ORBIT API", version="0.1.0", docs_url="/docs")
    api.state.orbit_context = ApiContext(orbit)
    api.state.orbit_metrics = RuntimeMetrics()

    @api.middleware("http")
    async def request_observability(request: Request, call_next: Any) -> Any:
        trace = RequestTrace(request.headers.get("x-request-id"))
        request.state.request_id = trace.request_id
        response = await call_next(request)
        response.headers["x-request-id"] = trace.request_id
        return response

    @api.get("/health")
    async def health(request: Request) -> dict[str, Any]:
        context = _context(request)
        status = context.app.health.overall()
        return {"status": "ok" if status is HealthStatus.HEALTHY else status.value, "state": context.app.state.value, "checks": [{"name": item.name, "status": item.status.value, "detail": item.detail} for item in context.app.health.check()]}

    @api.get("/ready")
    async def ready(request: Request) -> dict[str, Any]:
        context = _context(request)
        status = context.app.health.overall()
        if context.app.state.value != "ready" or status is HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=503, detail="ORBIT is not ready")
        return {"ready": True}

    @api.get("/v1/metrics")
    async def metrics(request: Request) -> dict[str, float | int]:
        return metrics_for(request).snapshot()

    @api.get("/v1/models")
    async def models(request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        return {"object": "list", "data": [{"id": model.spec.model_id, "object": "model", "owned_by": "orbit", "state": model.state.value, "path": str(model.path) if model.path else None, "capabilities": sorted(model.spec.capabilities)} for model in context.app.model_manager.all()]}

    @api.post("/v1/models")
    async def register_model(payload: ModelRegisterRequest, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        spec = ModelSpec(model_id=payload.id, display_name=payload.display_name, modality=payload.modality, size_bytes=payload.size_bytes, min_memory_bytes=payload.min_memory_bytes, capabilities=frozenset(payload.capabilities), runtimes=frozenset(payload.runtimes), tags=frozenset(payload.tags))
        managed = context.app.model_manager.register(spec)
        return {"id": managed.spec.model_id, "state": managed.state.value}

    @api.get("/v1/models/{model_id}")
    async def model_detail(model_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        managed = context.app.model_manager.get(model_id)
        if managed is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {model_id}")
        return {"id": model_id, "state": managed.state.value, "path": str(managed.path) if managed.path else None, "error": managed.error, "size_bytes": managed.spec.size_bytes, "modality": managed.spec.modality.value, "capabilities": sorted(managed.spec.capabilities)}

    @api.post("/v1/models/{model_id}/install")
    async def install_model(model_id: str, payload: ModelInstallRequest, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        managed = context.app.model_manager.get(model_id)
        if managed is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {model_id}")
        try:
            installed = ModelInstaller(context.app.model_manager).install(managed.spec, Path(payload.source_path), expected_sha256=payload.sha256)
        except ModelInstallError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"id": installed.spec.model_id, "state": installed.state.value, "path": str(installed.path), "size_bytes": installed.spec.size_bytes}

    @api.delete("/v1/models/{model_id}")
    async def remove_model(model_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        try:
            ModelInstaller(context.app.model_manager).remove(model_id)
        except ModelInstallError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"id": model_id, "state": "stopped", "removed": True}

    @api.post("/v1/models/{model_id}/verify")
    async def verify_model(model_id: str, payload: ModelVerifyRequest, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        try:
            report = ModelArtifactManager(context.app.model_manager).verify(model_id, Path(payload.path), expected_sha256=payload.sha256)
        except ModelArtifactError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"model": report.model_id, "path": str(report.path), "size_bytes": report.size_bytes, "sha256": report.sha256, "verified": report.verified}

    @api.get("/v1/system")
    async def system(request: Request) -> dict[str, Any]:
        context = _context(request)
        hardware = context.app.hardware
        if hardware is None:
            raise HTTPException(status_code=503, detail="ORBIT hardware profile unavailable")
        return {"platform": hardware.platform, "architecture": hardware.architecture, "memory_bytes": hardware.memory_bytes, "accelerators": [{"vendor": accelerator.vendor.value, "name": accelerator.name, "memory_bytes": accelerator.memory_bytes} for accelerator in hardware.accelerators]}

    @api.post("/v1/chat/completions")
    async def chat_completion(request: ChatCompletionRequest, http_request: Request) -> dict[str, Any]:
        context = _context(http_request)
        if context.app.models.get(request.model) is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {request.model}")
        runtime = context.app.runtimes.active
        if runtime is None:
            raise HTTPException(status_code=503, detail="no inference runtime is active")
        trace = RequestTrace(http_request.state.request_id)
        generation = GenerationRequest(prompt="\n".join(f"{message.role}: {message.content}" for message in request.messages), model=request.model, temperature=request.temperature, max_tokens=request.max_tokens)
        try:
            result = await RuntimeExecutor(runtime).execute(generation)
        except RuntimeExecutionError as exc:
            metrics_for(http_request).record(latency_ms=trace.elapsed_ms, tokens=0, failed=True)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        metrics_for(http_request).record(latency_ms=result.duration_ms, tokens=len(result.text.split()))
        return {"id": result.request_id, "object": "chat.completion", "model": request.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop"}], "usage": {"completion_ms": round(result.duration_ms, 3)}}

    return api


app = create_app()
