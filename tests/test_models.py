from pathlib import Path

from orbit.core.hardware import Accelerator, AcceleratorVendor, HardwareProfile
from orbit.core.model_store import ModelStore
from orbit.core.models import ModelCatalog, ModelSpec


def profile(vram_gb: int) -> HardwareProfile:
    return HardwareProfile(
        platform="test",
        architecture="x86_64",
        memory_bytes=32 * 1024**3,
        accelerators=(
            Accelerator(
                vendor=AcceleratorVendor.NVIDIA,
                name="Test GPU",
                memory_bytes=vram_gb * 1024**3,
            ),
        ),
    )


def test_catalog_recommends_memory_compatible_models() -> None:
    catalog = ModelCatalog(
        (
            ModelSpec("small", "Small", min_memory_bytes=4 * 1024**3, runtimes=frozenset({"llama.cpp"})),
            ModelSpec("large", "Large", min_memory_bytes=24 * 1024**3, runtimes=frozenset({"llama.cpp"})),
        )
    )

    recommendations = catalog.recommend(profile(8), "llama.cpp")
    assert [model.model_id for model in recommendations] == ["small"]


def test_model_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    original = ModelCatalog((ModelSpec("demo", "Demo", tags=frozenset({"chat"})),))
    store = ModelStore(path)

    store.save(original)
    restored = store.load()

    assert restored.get("demo") == original.get("demo")
