import pytest

from orbit.core.models import ModelSpec


def test_model_spec_rejects_empty_identity():
    with pytest.raises(ValueError, match="model_id"):
        ModelSpec("", "Demo")


def test_model_spec_rejects_negative_memory():
    with pytest.raises(ValueError, match="min_memory_bytes"):
        ModelSpec("demo", "Demo", min_memory_bytes=-1)


def test_catalog_limit_zero_returns_empty():
    from orbit.core.hardware import HardwareProfile
    from orbit.core.models import ModelCatalog

    catalog = ModelCatalog((ModelSpec("demo", "Demo"),))
    hardware = HardwareProfile("test", "x86_64", 8 * 1024**3)
    assert catalog.recommend(hardware, "llama.cpp", limit=0) == ()
