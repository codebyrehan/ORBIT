from pathlib import Path

from orbit.multimodal import VisionBackend, VoiceBackend


def test_voice_fallback_without_backend(tmp_path, monkeypatch):
    monkeypatch.delenv("ORBIT_STT_URL", raising=False)
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFF")
    result = VoiceBackend().transcribe(audio)
    assert result.ready is True
    assert "ORBIT_STT_URL" in result.detail


def test_vision_fallback_without_backend(tmp_path, monkeypatch):
    monkeypatch.delenv("ORBIT_VISION_URL", raising=False)
    image = tmp_path / "sample.png"
    image.write_bytes(b"PNG")
    result = VisionBackend().inspect(image)
    assert result.ready is True
    assert "ORBIT_VISION_URL" in result.detail
