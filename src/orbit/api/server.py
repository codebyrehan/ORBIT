"""FastAPI application exposing ORBIT's stable control-plane surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.runtime import GenerationRequest


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


@dataclass(slots=True)
class ApiContext:
    app: OrbitApp


def create_app(app: OrbitApp | None = None) -> FastAPI:
    """Create an API instance with an isolated ORBIT application context."""
    orbit = app or OrbitApp(OrbitConfig.default())
    if orbit.state.value not in {"ready", "starting"}:
        orbit.start()

    api = FastAPI(title="ORBIT API", version="0.1.0-dev", docs_url="/docs")
    context = ApiContext(orbit)

    @api.get("/health")
    async def health() -> dict[str, Any]:
        hardware = context.app.hardware
        return {
            "status": "ok",
            "state": context.app.state.value,
            "platform": hardware.platform if hardware else None,
        }

    @api.get("/v1/models")
    async def models() -> dict[str, Any]:
        data = [
            {
                "id": model.model_id,
                "object": "model",
                "owned_by": "orbit",
                "capabilities": sorted(model.capabilities),
            }
            for model in context.app.models.all()
        ]
        return {"object": "list", "data": data}

    @api.get("/v1/system")
    async def system() -> dict[str, Any]:
        hardware = context.app.hardware
        if hardware is None:
            raise HTTPException(status_code=503, detail="ORBIT is not initialized")
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
    async def chat_completion(request: ChatCompletionRequest) -> dict[str, Any]:
        runtime = context.app.runtimes.get("llama.cpp") or context.app.runtimes.active
        if runtime is None:
            raise HTTPException(status_code=503, detail="no inference runtime is registered")
        if context.app.models.get(request.model) is None:
            raise HTTPException(status_code=404, detail=f"unknown model: {request.model}")

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
        text = "".join(chunks)
        return {
            "id": "orbit-chat-completion",
            "object": "chat.completion",
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }

    return api


app = create_app()
