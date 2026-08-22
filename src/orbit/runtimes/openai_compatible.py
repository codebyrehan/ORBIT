"""Generic OpenAI-compatible remote inference runtime."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo


@dataclass(slots=True)
class OpenAICompatibleRuntime(RuntimeAdapter):
    """Connect ORBIT to any OpenAI-compatible chat-completions endpoint."""

    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 60.0
    runtime_name: str = "openai-compatible"

    @classmethod
    def from_env(cls) -> "OpenAICompatibleRuntime":
        return cls(
            base_url=os.getenv("ORBIT_OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("ORBIT_OPENAI_API_KEY") or None,
            timeout=float(os.getenv("ORBIT_OPENAI_TIMEOUT", "60")),
            runtime_name=os.getenv("ORBIT_OPENAI_RUNTIME_NAME", "openai-compatible"),
        )

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            name=self.runtime_name,
            version="openai-compatible",
            capabilities=frozenset({"text-generation", "chat", "streaming", "openai-compatible", "remote"}),
        )

    async def health(self) -> bool:
        return await asyncio.to_thread(self._health_sync)

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._generate(request)

    async def _generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        text = await asyncio.to_thread(self._generate_sync, request)
        yield text

    def _health_sync(self) -> bool:
        request = Request(self._url("/models"), headers=self._headers(), method="GET")
        try:
            with urlopen(request, timeout=min(self.timeout, 10.0)) as response:
                status = cast(int, response.status)
                return 200 <= status < 300
        except (OSError, URLError, HTTPError):
            return False

    def _generate_sync(self, request: GenerationRequest) -> str:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        http_request = Request(
            self._url("/chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, HTTPError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"OpenAI-compatible request failed: {exc}") from exc
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI-compatible endpoint returned an invalid chat response") from exc
        if not isinstance(text, str):
            raise RuntimeError("OpenAI-compatible endpoint returned non-text content")
        return text

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "ORBIT/0.2"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path
