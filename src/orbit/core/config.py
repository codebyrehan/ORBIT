"""Configuration primitives for ORBIT.

The first foundation release deliberately keeps configuration small and typed.
Higher-level configuration sources can be layered on top later without making
environment variables the architecture's primary interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OrbitConfig:
    """Immutable process configuration."""

    data_dir: Path
    log_level: str = "INFO"
    privacy_mode: str = "strict"

    @classmethod
    def default(cls, home: Path | None = None) -> "OrbitConfig":
        base = home if home is not None else Path.home()
        return cls(data_dir=base / ".orbit")

    def ensure_directories(self) -> None:
        """Create ORBIT's local state directory when needed."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
