from __future__ import annotations

from pathlib import Path

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig


def test_production_data_directory_is_configurable_and_isolated(tmp_path: Path) -> None:
    data_dir = tmp_path / "orbit-data"
    app = OrbitApp(OrbitConfig(data_dir=data_dir))

    assert app.config.data_dir == data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    assert data_dir.is_dir()


def test_production_config_does_not_write_outside_data_directory(tmp_path: Path) -> None:
    root = tmp_path / "orbit-data"
    app = OrbitApp(OrbitConfig(data_dir=root))
    root.mkdir(parents=True, exist_ok=True)

    assert app.config.data_dir.resolve().is_relative_to(tmp_path.resolve())
    assert not (tmp_path / "orbit.db").exists()
