"""Runtime-neutral multimodal contracts with optional HTTP backends."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MediaAnalysis:
    media_id: str
    kind: str
    ready: bool
    backend: str
    detail: str


class VoiceBackend:
    """Speech backend contract with an optional OpenAI-compatible HTTP adapter."""

    name = "voice-adapter"

    def transcribe(self, path: Path) -> MediaAnalysis:
        endpoint = os.getenv("ORBIT_STT_URL")
        if not endpoint:
            return MediaAnalysis(path.stem, "audio", path.exists(), self.name, "audio artifact accepted; set ORBIT_STT_URL to activate remote transcription")
        if not path.exists():
            return MediaAnalysis(path.stem, "audio", False, self.name, "audio artifact does not exist")
        try:
            result = _post_json(endpoint, {"audio_base64": base64.b64encode(path.read_bytes()).decode(), "filename": path.name})
            text = str(result.get("text", "")).strip()
            return MediaAnalysis(path.stem, "audio", bool(text), result.get("backend", endpoint), text or "STT backend returned no transcription")
        except Exception as exc:
            return MediaAnalysis(path.stem, "audio", False, self.name, f"STT backend error: {exc}")


class VisionBackend:
    """Image understanding contract with an optional HTTP adapter."""

    name = "vision-adapter"

    def inspect(self, path: Path) -> MediaAnalysis:
        endpoint = os.getenv("ORBIT_VISION_URL")
        if not endpoint:
            return MediaAnalysis(path.stem, "image", path.exists(), self.name, "image artifact accepted; set ORBIT_VISION_URL to activate remote vision")
        if not path.exists():
            return MediaAnalysis(path.stem, "image", False, self.name, "image artifact does not exist")
        try:
            result = _post_json(endpoint, {"image_base64": base64.b64encode(path.read_bytes()).decode(), "filename": path.name})
            detail = str(result.get("text") or result.get("description") or "").strip()
            return MediaAnalysis(path.stem, "image", bool(detail), result.get("backend", endpoint), detail or "vision backend returned no analysis")
        except Exception as exc:
            return MediaAnalysis(path.stem, "image", False, self.name, f"vision backend error: {exc}")


def _post_json(endpoint: str, payload: dict[str, object]) -> dict[str, object]:
    """POST JSON to a configured private multimodal service without adding a dependency."""
    body = json.dumps(payload).encode()
    request = urllib.request.Request(endpoint, data=body, method="POST", headers={"Content-Type": "application/json"})
    timeout = float(os.getenv("ORBIT_MULTIMODAL_TIMEOUT", "30"))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode())
    if not isinstance(data, dict):
        raise ValueError("backend response must be a JSON object")
    return data
