"""Configuration primitives for ORBIT."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from orbit.core.security_policy import resolve_api_token


@dataclass(frozen=True, slots=True)
class OrbitConfig:
    """Immutable process configuration."""

    data_dir: Path
    log_level: str = "INFO"
    privacy_mode: str = "strict"
    api_key: str | None = None
    rate_limit_per_minute: int = 120
    rate_limit_burst: int = 20

    @classmethod
    def default(cls, home: Path | None = None) -> OrbitConfig:
        """Build the default runtime configuration, honoring environment overrides."""
        return cls.from_env(home)

    @classmethod
    def from_env(cls, home: Path | None = None) -> OrbitConfig:
        base = home if home is not None else Path.home()
        rate_limit = int(os.getenv("ORBIT_RATE_LIMIT_PER_MINUTE", "120"))
        burst = int(os.getenv("ORBIT_RATE_LIMIT_BURST", "20"))
        if rate_limit <= 0 or burst <= 0:
            raise ValueError("rate limits must be positive")
        privacy_mode = os.getenv("ORBIT_PRIVACY_MODE", "strict")
        if privacy_mode not in {"strict", "standard"}:
            raise ValueError("ORBIT_PRIVACY_MODE must be strict or standard")
        return cls(
            data_dir=Path(os.getenv("ORBIT_DATA_DIR", str(base / ".orbit"))),
            log_level=os.getenv("ORBIT_LOG_LEVEL", "INFO"),
            privacy_mode=privacy_mode,
            api_key=resolve_api_token(None),
            rate_limit_per_minute=rate_limit,
            rate_limit_burst=burst,
        )

    def ensure_directories(self) -> None:
        """Create ORBIT's local state directory when needed."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.data_dir.chmod(0o700)
        except OSError:
            pass
