"""Deterministic built-in runtime used to validate the full product path."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo


@dataclass(slots=True)
class DemoRuntime(RuntimeAdapter):
    """Small dependency-free runtime for production control-plane smoke tests."""

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            name="orbit-demo",
            version="1.0",
            capabilities=frozenset({"text-generation", "chat", "streaming", "demo"}),
        )

    async def health(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._generate(request)

    async def _generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        prompt = request.prompt.splitlines()[-1].strip()
        if prompt.lower().startswith("user:"):
            prompt = prompt[5:].strip()
        text = (
            "ORBIT demo runtime is active. "
            f"You asked: {prompt} "
            "This response proves the browser → API → router → orchestrator → runtime path."
        )
        words = text.split(" ")
        limit = request.max_tokens or len(words)
        for index, word in enumerate(words[:limit]):
            yield word + (" " if index < min(limit, len(words)) - 1 else "")
