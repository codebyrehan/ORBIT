"""Fail-fast smoke check for ORBIT's configured inference provider."""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


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
    if endpoint.endswith("/v1"):
        url = endpoint + "/models"
    else:
        url = endpoint + "/v1/models"
    headers = {}
    key = os.getenv("ORBIT_OPENAI_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=float(os.getenv("ORBIT_PROVIDER_SMOKE_TIMEOUT", "10"))) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            if response.status != 200:
                print(f"PROVIDER_HTTP_{response.status}")
                return 1
            print(f"PROVIDER_OK {endpoint}")
            if model:
                print(f"MODEL_CONFIGURED {model}")
            print(body[:1000])
            return 0
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"PROVIDER_UNREACHABLE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
