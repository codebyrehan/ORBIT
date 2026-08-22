from pathlib import Path

from orbit.core.model_manager import ModelManager, ModelState
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelSpec


def test_model_manager_registers_and_restores(tmp_path: Path) -> None:
    store = ModelStore(tmp_path / "models.json")
    manager = ModelManager(store, tmp_path / "models")
    spec = ModelSpec(model_id="demo", display_name="Demo", runtimes=frozenset({"llama.cpp"}))

    registered = manager.register(spec)
    assert registered.state == ModelState.REGISTERED

    restored = ModelManager(store, tmp_path / "models")
    assert restored.get("demo") is not None
    assert restored.get("demo").spec.model_id == "demo"


def test_model_manager_marks_existing_file_ready(tmp_path: Path) -> None:
    store = ModelStore(tmp_path / "models.json")
    manager = ModelManager(store, tmp_path / "models")
    manager.register(ModelSpec(model_id="demo", display_name="Demo"))
    model_path = tmp_path / "models" / "demo.gguf"
    model_path.write_bytes(b"model")

    ready = manager.mark_ready("demo", model_path)
    assert ready.state == ModelState.READY
    assert ready.path == model_path

    restored = ModelManager(store, tmp_path / "models")
    assert restored.get("demo").state == ModelState.READY


def test_model_manager_rejects_missing_file(tmp_path: Path) -> None:
    manager = ModelManager(ModelStore(tmp_path / "models.json"), tmp_path / "models")
    manager.register(ModelSpec(model_id="demo", display_name="Demo"))

    try:
        manager.mark_ready("demo", tmp_path / "missing.gguf")
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("missing model file should be rejected")
