"""Fail-fast smoke check for ORBIT's configured inference provider."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _request(url: str, *, method: str = "GET", payload: dict | None = None, key: str = "") -> tuple[int, str]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=float(os.getenv("ORBIT_PROVIDER_SMOKE_TIMEOUT", "10"))) as response:
        return response.status, response.read(16384).decode("utf-8", errors="replace")


def main() -> int:
    base = os.getenv("ORBIT_OPENAI_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("ORBIT_OPENAI_MODEL", "").strip()
    llama = os.getenv("ORBIT_LLAMA_CPP_URL", "").strip().rstrip("/")
    if not base and not llama:
        print("NO_PROVIDER_CONFIGURED")
        return 2
    if not model and not llama:
        print("NO_MODEL_CONFIGURED")
        return 2

    endpoint = base or llama
    models_url = endpoint + "/models" if endpoint.endswith("/v1") else endpoint + "/v1/models"
    key = os.getenv("ORBIT_OPENAI_API_KEY", "").strip()

    try:
        status, body = _request(models_url, key=key)
        if status != 200:
            print(f"PROVIDER_HTTP_{status}")
            return 1
        print(f"PROVIDER_OK {endpoint}")
        if model:
            print(f"MODEL_CONFIGURED {model}")

        if not model or os.getenv("ORBIT_PROVIDER_SMOKE_CHAT", "1").lower() in {"0", "false", "no"}:
            print(body[:2000])
            return 0

        chat_url = endpoint + "/chat/completions" if endpoint.endswith("/v1") else endpoint + "/v1/chat/completions"
        status, response = _request(
            chat_url,
            method="POST",
            key=key,
            payload={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: ORBIT_SMOKE_OK"}],
                "temperature": 0,
                "max_tokens": 16,
                "stream": False,
            },
        )
        if status != 200:
            print(f"INFERENCE_HTTP_{status}")
            print(response[:2000])
            return 1
        data = json.loads(response)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "ORBIT_SMOKE_OK" not in content:
            print(f"INFERENCE_UNEXPECTED_RESPONSE: {content[:500]}")
            return 1
        print("INFERENCE_OK ORBIT_SMOKE_OK")
        return 0
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError, IndexError) as exc:
        print(f"PROVIDER_SMOKE_FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
