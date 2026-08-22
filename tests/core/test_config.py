from __future__ import annotations

from pathlib import Path

import pytest

from orbit.core.config import OrbitConfig


def test_config_from_env_loads_validated_runtime_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ORBIT_API_TOKEN", "t" * 40)
    monkeypatch.setenv("ORBIT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ORBIT_PRIVACY_MODE", "strict")
    monkeypatch.setenv("ORBIT_RATE_LIMIT_PER_MINUTE", "60")
    monkeypatch.setenv("ORBIT_RATE_LIMIT_BURST", "10")

    config = OrbitConfig.from_env()

    assert config.data_dir == tmp_path / "state"
    assert config.api_key == "t" * 40
    assert config.log_level == "DEBUG"
    assert config.rate_limit_per_minute == 60
    assert config.rate_limit_burst == 10


def test_config_rejects_invalid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORBIT_RATE_LIMIT_PER_MINUTE", "0")
    with pytest.raises(ValueError):
        OrbitConfig.from_env()

    monkeypatch.setenv("ORBIT_RATE_LIMIT_PER_MINUTE", "120")
    monkeypatch.setenv("ORBIT_PRIVACY_MODE", "public")
    with pytest.raises(ValueError):
        OrbitConfig.from_env()
