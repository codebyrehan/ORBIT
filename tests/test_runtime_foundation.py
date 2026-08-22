import os

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.hardware import Accelerator, AcceleratorVendor, HardwareProfile
from orbit.core.models import ModelCatalog, ModelSpec
from orbit.core.runtime import RuntimeAdapter, RuntimeInfo
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import ResourceScheduler


class FakeRuntime(RuntimeAdapter):
    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo("fake", "1.0", frozenset({"text"}))

    async def health(self) -> bool:
        return True

    async def generate(self, request):
        yield request.prompt


def hardware() -> HardwareProfile:
    return HardwareProfile(
        platform="linux",
        architecture="x86_64",
        memory_bytes=32 * 1024**3,
        accelerators=(
            Accelerator(AcceleratorVendor.NVIDIA, "Test GPU", 16 * 1024**3),
        ),
    )


def test_catalog_recommends_compatible_model():
    catalog = ModelCatalog(
        (
            ModelSpec("small", "Small", min_memory_bytes=8 * 1024**3, runtimes=frozenset({"fake"})),
            ModelSpec("large", "Large", min_memory_bytes=32 * 1024**3, runtimes=frozenset({"fake"})),
        )
    )
    recommendations = catalog.recommend(hardware(), "fake")
    assert [model.model_id for model in recommendations] == ["small"]


def test_scheduler_creates_placement():
    model = ModelSpec("small", "Small", min_memory_bytes=8 * 1024**3, runtimes=frozenset({"fake"}))
    placement = ResourceScheduler(hardware()).place(model, "fake")
    assert placement is not None
    assert placement.model_id == "small"


def test_runtime_manager_selects_registered_adapter():
    manager = RuntimeManager()
    runtime = FakeRuntime()
    manager.register(runtime)
    assert manager.select("fake") is runtime
    assert manager.active is runtime


def test_openai_compatible_runtime_can_be_configured_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ORBIT_OPENAI_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("ORBIT_OPENAI_MODEL", "local-model")
    monkeypatch.delenv("ORBIT_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ORBIT_LLAMA_CPP_URL", raising=False)
    monkeypatch.delenv("ORBIT_LLAMA_CPP_MODEL", raising=False)
    monkeypatch.setenv("ORBIT_ENABLE_DEMO_MODEL", "false")
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))
    app.start()
    try:
        assert "openai-compatible" in app.runtimes.names()
        assert [m.model_id for m in app.models.all()] == ["local-model"]
    finally:
        app.stop()
