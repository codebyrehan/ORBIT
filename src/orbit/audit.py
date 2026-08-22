"""Durable, privacy-conscious audit events for the ORBIT control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock


@dataclass(frozen=True, slots=True)
class AuditEvent:
    timestamp: str
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    authenticated: bool


class AuditLog:
    """Append-only JSONL audit log with bounded reads."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def record(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        authenticated: bool,
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 3),
            authenticated=authenticated,
        )
        line = json.dumps(asdict(event), separators=(",", ":"), sort_keys=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return event

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not self.path.exists():
            return []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        events: list[dict[str, object]] = []
        for line in reversed(lines[-limit:]):
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    events.append(value)
        return events
