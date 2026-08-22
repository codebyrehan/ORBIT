"""Request lifecycle tracking for ORBIT's inference control plane."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Final


_ACTIVE: Final[str] = "active"
_COMPLETED: Final[str] = "completed"
_FAILED: Final[str] = "failed"
_CANCELLED: Final[str] = "cancelled"


@dataclass(frozen=True, slots=True)
class RequestRecord:
    request_id: str
    model_id: str
    runtime_name: str
    state: str
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    tokens: int = 0


class RequestManager:
    """Track bounded in-memory request state without retaining prompt contents."""

    def __init__(self, max_records: int = 1000) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be positive")
        self.max_records = max_records
        self._records: dict[str, RequestRecord] = {}
        self._lock = Lock()

    def start(self, request_id: str, model_id: str, runtime_name: str) -> RequestRecord:
        record = RequestRecord(request_id, model_id, runtime_name, _ACTIVE, self._now())
        with self._lock:
            self._records[request_id] = record
            self._trim()
        return record

    def complete(self, request_id: str, *, tokens: int = 0) -> RequestRecord:
        return self._finish(request_id, _COMPLETED, tokens=tokens)

    def fail(self, request_id: str, error: str, *, tokens: int = 0) -> RequestRecord:
        return self._finish(request_id, _FAILED, error=error, tokens=tokens)

    def cancel(self, request_id: str) -> RequestRecord:
        return self._finish(request_id, _CANCELLED)

    def get(self, request_id: str) -> RequestRecord | None:
        with self._lock:
            return self._records.get(request_id)

    def recent(self, limit: int = 100) -> list[RequestRecord]:
        if not 1 <= limit <= self.max_records:
            raise ValueError(f"limit must be between 1 and {self.max_records}")
        with self._lock:
            return list(self._records.values())[-limit:][::-1]

    def _finish(self, request_id: str, state: str, *, error: str | None = None, tokens: int = 0) -> RequestRecord:
        with self._lock:
            current = self._records.get(request_id)
            if current is None:
                raise KeyError(f"unknown request: {request_id}")
            if current.state != _ACTIVE:
                return current
            updated = RequestRecord(current.request_id, current.model_id, current.runtime_name, state, current.created_at, self._now(), error, max(0, tokens))
            self._records[request_id] = updated
            return updated

    def _trim(self) -> None:
        excess = len(self._records) - self.max_records
        if excess > 0:
            for request_id in list(self._records)[:excess]:
                del self._records[request_id]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
