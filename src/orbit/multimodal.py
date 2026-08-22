"""Runtime-neutral multimodal contracts for voice and vision backends."""
from __future__ import annotations

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
    """Optional speech backend contract; local implementations can plug in later."""

    name = "voice-adapter"

    def transcribe(self, path: Path) -> MediaAnalysis:
        return MediaAnalysis(path.stem, "audio", path.exists(), self.name, "audio artifact accepted; transcription backend is replaceable")


class VisionBackend:
    """Optional image understanding backend contract."""

    name = "vision-adapter"

    def inspect(self, path: Path) -> MediaAnalysis:
        return MediaAnalysis(path.stem, "image", path.exists(), self.name, "image artifact accepted; vision backend is replaceable")
