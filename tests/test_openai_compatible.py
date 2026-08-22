from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from orbit.core.runtime import GenerationRequest
from orbit.runtimes.openai_compatible import OpenAICompatibleRuntime


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "mock-model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        assert payload["model"] == "mock-model"
        body = json.dumps({"choices": [{"message": {"role": "assistant", "content": "mock response"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        return


@pytest.fixture()
def server() -> str:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


@pytest.mark.asyncio
async def test_openai_compatible_runtime(server: str) -> None:
    runtime = OpenAICompatibleRuntime(base_url=server, api_key="test-key")
    assert await runtime.health() is True
    chunks = [chunk async for chunk in runtime.generate(GenerationRequest("hello", "mock-model"))]
    assert chunks == ["mock response"]
