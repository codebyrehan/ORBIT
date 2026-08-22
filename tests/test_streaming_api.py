from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient

from orbit.api.server import create_app
from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.models import ModelSpec
from orbit.core.runtime import GenerationRequest, RuntimeAdapter, RuntimeInfo


class StreamingRuntime(RuntimeAdapter):
    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo("stream-test", "1.0", frozenset({"text"}))

    async def health(self) -> bool:
        return True

    async def _tokens(self, request: GenerationRequest) -> AsyncIterator[str]:
        yield "hello "
        yield "world"

    def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        return self._tokens(request)


def make_client(tmp_path: Path) -> TestClient:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    app.models.register(ModelSpec("demo", "Demo", runtimes=frozenset({"stream-test"})))
    app.runtimes.register(StreamingRuntime())
    return TestClient(create_app(app))


def test_streaming_chat_completion_returns_sse_chunks(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "chat.completion.chunk" in response.text
    assert '"content":"hello "' in response.text
    assert '"content":"world"' in response.text
    assert '"finish_reason":"stop"' in response.text
    assert "data: [DONE]" in response.text


def test_non_streaming_chat_completion_remains_compatible(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "demo",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["runtime"] == "stream-test"
    assert body["choices"][0]["message"]["content"] == "hello world"
