from pathlib import Path

from orbit.core.app import OrbitApp
from orbit.core.config import OrbitConfig
from orbit.core.hardware import Accelerator, AcceleratorVendor, HardwareProfile
from orbit.core.lifecycle import LifecycleState


def test_app_starts_and_creates_state_directory(tmp_path: Path) -> None:
    app = OrbitApp(OrbitConfig(data_dir=tmp_path / ".orbit"))

    app.start()

    assert app.state is LifecycleState.READY
    assert (tmp_path / ".orbit").is_dir()


def test_app_stops() -> None:
    app = OrbitApp(OrbitConfig.default())
    app.start()
    app.stop()

    assert app.state is LifecycleState.STOPPED


def test_hardware_profile_sums_accelerator_memory() -> None:
    profile = HardwareProfile(
        platform="linux",
        architecture="x86_64",
        memory_bytes=32 * 1024**3,
        accelerators=(
            Accelerator(AcceleratorVendor.NVIDIA, "GPU A", 8 * 1024**3),
            Accelerator(AcceleratorVendor.NVIDIA, "GPU B", 12 * 1024**3),
        ),
    )

    assert profile.accelerator_memory_bytes == 20 * 1024**3
