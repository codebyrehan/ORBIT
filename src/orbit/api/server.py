"""FastAPI application exposing ORBIT's stable control-plane surface."""

from __future__ import annotations

from dataclasses import dataclass
import json
import secrets
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from orbit.api.observability import metrics_for
from orbit.api.rate_limit import RateLimiter
from orbit.api.runtime_control import RuntimeExecutionError, RuntimeExecutor
from orbit.audit import AuditLog
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.health import HealthStatus
from orbit.core.model_artifacts import ModelArtifactError, ModelArtifactManager
from orbit.core.model_installer import ModelInstallError, ModelInstaller
from orbit.core.models import ModelModality, ModelSpec
from orbit.core.router import RouteRequest
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
    runtime: str | None = Field(default=None, min_length=1)
    stream: bool = False


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


def _sync_catalog_to_manager(app: OrbitApp) -> None:
    if app.model_manager is None:
        return
    for spec in app.models.all():
        if app.model_manager.get(spec.model_id) is None:
            app.model_manager.register(spec)


def _model_payload(model: Any) -> dict[str, Any]:
    return {"id": model.spec.model_id, "object": "model", "owned_by": "orbit", "state": model.state.value, "path": str(model.path) if model.path else None, "capabilities": sorted(model.spec.capabilities)}


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()


def create_app(app: OrbitApp | None = None) -> FastAPI:
    configure_logging()
    orbit = app or OrbitApp(OrbitConfig.default())
    api = FastAPI(title="ORBIT API", version="0.1.0", docs_url="/docs")
    api.state.orbit_context = ApiContext(orbit)
    api.state.orbit_metrics = RuntimeMetrics()
    api.state.orbit_audit = AuditLog(orbit.config.data_dir / "audit.jsonl")
    limiter = RateLimiter(orbit.config.rate_limit_per_minute, orbit.config.rate_limit_burst)

    @api.middleware("http")
    async def request_security(request: Request, call_next: Any) -> Any:
        request.state.authenticated = orbit.config.api_key is None
        if request.url.path.startswith("/v1/"):
            if orbit.config.api_key is not None:
                authorization = request.headers.get("authorization", "")
                scheme, _, token = authorization.partition(" ")
                if scheme.lower() != "bearer" or not token or not secrets.compare_digest(token, orbit.config.api_key):
                    return JSONResponse(status_code=401, content={"detail": "authentication required"}, headers={"WWW-Authenticate": "Bearer"})
                request.state.authenticated = True
            identity = request.headers.get("authorization") or (request.client.host if request.client else "unknown")
            allowed, retry_after = limiter.allow(identity)
            if not allowed:
                return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"}, headers={"Retry-After": str(retry_after)})
        return await call_next(request)

    @api.middleware("http")
    async def request_observability(request: Request, call_next: Any) -> Any:
        trace = RequestTrace(request.headers.get("x-request-id"))
        request.state.request_id = trace.request_id
        response = await call_next(request)
        response.headers["x-request-id"] = trace.request_id
        return response

    @api.middleware("http")
    async def request_audit(request: Request, call_next: Any) -> Any:
        trace = RequestTrace()
        try:
            response = await call_next(request)
        except Exception:
            api.state.orbit_audit.record(request_id=getattr(request.state, "request_id", trace.request_id), method=request.method, path=request.url.path, status_code=500, duration_ms=trace.elapsed_ms, authenticated=bool(getattr(request.state, "authenticated", False)))
            raise
        api.state.orbit_audit.record(request_id=getattr(request.state, "request_id", trace.request_id), method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=trace.elapsed_ms, authenticated=bool(getattr(request.state, "authenticated", False)))
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

    @api.get("/v1/audit/events")
    async def audit_events(request: Request, limit: int = 100) -> dict[str, Any]:
        try:
            events = api.state.orbit_audit.recent(limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"object": "list", "data": events}

    @api.get("/v1/requests")
    async def requests(request: Request, limit: int = 100) -> dict[str, Any]:
        context = _context(request)
        try:
            records = context.app.request_manager.recent(limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"object": "list", "data": [{"request_id": item.request_id, "model": item.model_id, "runtime": item.runtime_name, "state": item.state, "created_at": item.created_at, "completed_at": item.completed_at, "error": item.error, "tokens": item.tokens} for item in records]}

    @api.get("/v1/requests/{request_id}")
    async def request_detail(request_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        record = context.app.request_manager.get(request_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown request: {request_id}")
        return {"request_id": record.request_id, "model": record.model_id, "runtime": record.runtime_name, "state": record.state, "created_at": record.created_at, "completed_at": record.completed_at, "error": record.error, "tokens": record.tokens}

    @api.post("/v1/requests/{request_id}/cancel")
    async def cancel_request(request_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        try:
            record = context.app.request_manager.cancel(request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"request_id": record.request_id, "state": record.state}

    @api.get("/v1/models")
    async def models(request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        _sync_catalog_to_manager(context.app)
        return {"object": "list", "data": [_model_payload(model) for model in context.app.model_manager.all()]}

    @api.post("/v1/models")
    async def register_model(payload: ModelRegisterRequest, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        spec = ModelSpec(model_id=payload.id, display_name=payload.display_name, modality=payload.modality, size_bytes=payload.size_bytes, min_memory_bytes=payload.min_memory_bytes, capabilities=frozenset(payload.capabilities), runtimes=frozenset(payload.runtimes), tags=frozenset(payload.tags))
        managed = context.app.model_manager.register(spec)
        context.app.models.register(spec)
        return _model_payload(managed)

    @api.get("/v1/models/{model_id}")
    async def model_detail(model_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        _sync_catalog_to_manager(context.app)
        managed = context.app.model_manager.get(model_id)
        if managed is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {model_id}")
        return {"id": model_id, "state": managed.state.value, "path": str(managed.path) if managed.path else None, "error": managed.error, "size_bytes": managed.spec.size_bytes, "modality": managed.spec.modality.value, "capabilities": sorted(managed.spec.capabilities)}

    @api.post("/v1/models/{model_id}/install")
    async def install_model(model_id: str, payload: ModelInstallRequest, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        _sync_catalog_to_manager(context.app)
        managed = context.app.model_manager.get(model_id)
        if managed is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {model_id}")
        try:
            installed = ModelInstaller(context.app.model_manager).install(managed.spec, Path(payload.source_path), expected_sha256=payload.sha256)
        except ModelInstallError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        context.app.models = context.app.model_store.load() if context.app.model_store is not None else context.app.models
        if context.app.router is not None:
            context.app.router.catalog = context.app.models
        return _model_payload(installed)

    @api.delete("/v1/models/{model_id}")
    async def remove_model(model_id: str, request: Request) -> dict[str, Any]:
        context = _context(request)
        if context.app.model_manager is None:
            raise HTTPException(status_code=503, detail="model manager unavailable")
        try:
            ModelInstaller(context.app.model_manager).remove(model_id)
        except ModelInstallError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if context.app.model_store is not None:
            context.app.models = context.app.model_store.load()
            if context.app.router is not None:
                context.app.router.catalog = context.app.models
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
    async def chat_completion(request: ChatCompletionRequest, http_request: Request) -> Any:
        context = _context(http_request)
        _sync_catalog_to_manager(context.app)
        if context.app.router is None:
            raise HTTPException(status_code=503, detail="inference router unavailable")
        trace = RequestTrace(http_request.state.request_id)
        prompt = "\n".join(f"{message.role}: {message.content}" for message in request.messages)
        try:
            decision = await context.app.router.route(RouteRequest(request.model, request.runtime))
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        generation = GenerationRequest(prompt=prompt, model=decision.model_id, temperature=request.temperature, max_tokens=request.max_tokens)
        executor = RuntimeExecutor(decision.plan.runtime)
        if not request.stream:
            try:
                result = await executor.execute(generation)
            except RuntimeExecutionError as exc:
                context.app.request_manager.fail(trace.request_id, str(exc))
                metrics_for(http_request).record(latency_ms=trace.elapsed_ms, tokens=0, failed=True)
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            context.app.request_manager.start(result.request_id, decision.model_id, decision.runtime_name)
            context.app.request_manager.complete(result.request_id, tokens=len(result.text.split()))
            metrics_for(http_request).record(latency_ms=result.duration_ms, tokens=len(result.text.split()))
            return {"id": result.request_id, "object": "chat.completion", "model": decision.model_id, "runtime": decision.runtime_name, "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop"}], "usage": {"completion_ms": round(result.duration_ms, 3)}}

        request_id = http_request.state.request_id
        context.app.request_manager.start(request_id, decision.model_id, decision.runtime_name)

        async def event_stream() -> AsyncIterator[bytes]:
            completion_id = f"chatcmpl-{request_id}"
            token_count = 0
            try:
                yield _sse({"id": completion_id, "object": "chat.completion.chunk", "model": decision.model_id, "runtime": decision.runtime_name, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})
                async for chunk in executor.stream(generation):
                    token_count += len(chunk.split())
                    yield _sse({"id": completion_id, "object": "chat.completion.chunk", "model": decision.model_id, "runtime": decision.runtime_name, "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]})
                context.app.request_manager.complete(request_id, tokens=token_count)
                metrics_for(http_request).record(latency_ms=trace.elapsed_ms, tokens=token_count)
                yield _sse({"id": completion_id, "object": "chat.completion.chunk", "model": decision.model_id, "runtime": decision.runtime_name, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
                yield b"data: [DONE]\n\n"
            except RuntimeExecutionError as exc:
                context.app.request_manager.fail(request_id, str(exc), tokens=token_count)
                metrics_for(http_request).record(latency_ms=trace.elapsed_ms, tokens=token_count, failed=True)
                yield _sse({"id": completion_id, "object": "error", "error": {"message": "generation failed", "type": "runtime_error"}})
            except asyncio.CancelledError:
                context.app.request_manager.cancel(request_id)
                raise

        return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

    return api


app = create_app()
