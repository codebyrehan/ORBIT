"""HTTP adapter for a llama.cpp server exposing its OpenAI-compatible API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import cast
from urllib.error import URLError
from urllib.request import Request, urlopen
import asyncio
import json

from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo


@dataclass(slots=True)
class LlamaCppRuntime(RuntimeAdapter):
    """Connect ORBIT to an already-running llama.cpp HTTP server."""

    base_url: str = "http://127.0.0.1:8080"
    timeout: float = 5.0
    runtime_version: str = "unknown"

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            name="llama.cpp",
            version=self.runtime_version,
            capabilities=frozenset({"text-generation", "streaming", "openai-compatible"}),
        )

    async def health(self) -> bool:
        return await asyncio.to_thread(self._health_sync)

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._generate(request)

    async def _generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        text = await asyncio.to_thread(self._generate_sync, request)
        yield text

    def _health_sync(self) -> bool:
        request = Request(self._url("/health"), method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = cast(int, response.status)
                return 200 <= status < 300
        except (OSError, URLError):
            return False

    def _generate_sync(self, request: GenerationRequest) -> str:
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        http_request = Request(
            self._url("/v1/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"llama.cpp request failed: {exc}") from exc

        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError("llama.cpp returned no completion choices")
        text = choices[0].get("text")
        if not isinstance(text, str):
            raise TypeError("llama.cpp returned an invalid completion")
        return text

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path
