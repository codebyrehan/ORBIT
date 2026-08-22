"""FastAPI application exposing ORBIT's stable control-plane surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.health import HealthStatus
from orbit.core.runtime import GenerationRequest


class ChatMessage(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


@dataclass(slots=True)
class ApiContext:
    app: OrbitApp


def _context(request: Request) -> ApiContext:
    context = request.app.state.orbit_context
    if not isinstance(context, ApiContext):
        raise RuntimeError("ORBIT API context is unavailable")
    if context.app.state.value not in {"ready", "starting"}:
        context.app.start()
    return context


def create_app(app: OrbitApp | None = None) -> FastAPI:
    orbit = app or OrbitApp(OrbitConfig.default())
    api = FastAPI(title="ORBIT API", version="0.1.0", docs_url="/docs")
    api.state.orbit_context = ApiContext(orbit)

    @api.get("/health")
    async def health(request: Request) -> dict[str, Any]:
        context = _context(request)
        status = context.app.health.overall()
        return {
            "status": "ok" if status is HealthStatus.HEALTHY else status.value,
            "state": context.app.state.value,
            "checks": [
                {"name": item.name, "status": item.status.value, "detail": item.detail}
                for item in context.app.health.check()
            ],
        }

    @api.get("/ready")
    async def ready(request: Request) -> dict[str, Any]:
        context = _context(request)
        status = context.app.health.overall()
        if context.app.state.value != "ready" or status is HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=503, detail="ORBIT is not ready")
        return {"ready": True}

    @api.get("/v1/models")
    async def models(request: Request) -> dict[str, Any]:
        context = _context(request)
        return {
            "object": "list",
            "data": [
                {
                    "id": model.model_id,
                    "object": "model",
                    "owned_by": "orbit",
                    "capabilities": sorted(model.capabilities),
                }
                for model in context.app.models.all()
            ],
        }

    @api.get("/v1/system")
    async def system(request: Request) -> dict[str, Any]:
        context = _context(request)
        hardware = context.app.hardware
        if hardware is None:
            raise HTTPException(status_code=503, detail="ORBIT hardware profile unavailable")
        return {
            "platform": hardware.platform,
            "architecture": hardware.architecture,
            "memory_bytes": hardware.memory_bytes,
            "accelerators": [
                {
                    "vendor": accelerator.vendor.value,
                    "name": accelerator.name,
                    "memory_bytes": accelerator.memory_bytes,
                }
                for accelerator in hardware.accelerators
            ],
        }

    @api.post("/v1/chat/completions")
    async def chat_completion(
        request: ChatCompletionRequest, http_request: Request
    ) -> dict[str, Any]:
        context = _context(http_request)
        if context.app.models.get(request.model) is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {request.model}")
        runtime = context.app.runtimes.active
        if runtime is None:
            raise HTTPException(status_code=503, detail="no inference runtime is active")
        prompt = "\n".join(f"{message.role}: {message.content}" for message in request.messages)
        generation = GenerationRequest(
            prompt=prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        chunks: list[str] = []
        async for chunk in runtime.generate(generation):
            chunks.append(chunk)
        return {
            "id": "orbit-chat-completion",
            "object": "chat.completion",
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(chunks)},
                "finish_reason": "stop",
            }],
        }

    return api


app = create_app()
