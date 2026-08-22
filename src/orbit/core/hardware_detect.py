"""Best-effort hardware discovery for the ORBIT control plane.

Detection is intentionally dependency-light. Optional vendor utilities are
queried when present, while every platform still receives a useful profile.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

from orbit.core.hardware import Accelerator, AcceleratorVendor, HardwareProfile


def _system_memory() -> int | None:
    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            size = os.sysconf("SC_PAGE_SIZE")
            if pages > 0 and size > 0:
                return pages * size
        except (OSError, ValueError):
            pass
    return None


def _nvidia_accelerators() -> tuple[Accelerator, ...]:
    command = shutil.which("nvidia-smi")
    if not command:
        return ()
    try:
        result = subprocess.run(
            [command, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ()

    accelerators: list[Accelerator] = []
    for line in result.stdout.splitlines():
        name, _, memory = line.partition(",")
        name = name.strip()
        try:
            memory_bytes = int(memory.strip()) * 1024 * 1024
        except ValueError:
            memory_bytes = None
        if name:
            accelerators.append(Accelerator(AcceleratorVendor.NVIDIA, name, memory_bytes))
    return tuple(accelerators)


def _apple_accelerators() -> tuple[Accelerator, ...]:
    if platform.system() != "Darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
        return ()
    return (Accelerator(AcceleratorVendor.APPLE, "Apple Silicon unified memory"),)


def detect_hardware() -> HardwareProfile:
    """Return a normalized, best-effort description of the current host."""

    accelerators = _nvidia_accelerators() or _apple_accelerators()
    if not accelerators:
        accelerators = (Accelerator(AcceleratorVendor.CPU, platform.processor() or "CPU"),)

    return HardwareProfile(
        platform=platform.system().lower() or "unknown",
        architecture=platform.machine().lower() or "unknown",
        memory_bytes=_system_memory(),
        accelerators=accelerators,
    )
