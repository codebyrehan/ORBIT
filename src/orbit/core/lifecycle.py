"""Application lifecycle state for the ORBIT control plane."""

from __future__ import annotations

from enum import StrEnum


class LifecycleState(StrEnum):
    CREATED = "created"
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
