"""Request lifecycle tracking for ORBIT's inference control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Final


_ACTIVE: Final[str] = "active"
_COMPLETED: Final[str] = "completed"
_FAILED: Final[str] = "failed"
_CANCELLED: Final[str] = "cancelled"
_RECOVERY_ERROR: Final[str] = "request interrupted by process restart"


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
    """Track bounded request state and recover interrupted requests from JSONL."""

    def __init__(self, max_records: int = 1000, journal_path: Path | None = None) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be positive")
        self.max_records = max_records
        self.journal_path = journal_path
        self.recovered_count = 0
        self._records: dict[str, RequestRecord] = {}
        self._lock = Lock()
        if journal_path is not None:
            self._load()

    def start(self, request_id: str, model_id: str, runtime_name: str) -> RequestRecord:
        record = RequestRecord(request_id, model_id, runtime_name, _ACTIVE, self._now())
        with self._lock:
            self._records[request_id] = record
            self._trim()
            self._persist(record)
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
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._lock:
            effective_limit = min(limit, self.max_records)
            return list(self._records.values())[-effective_limit:][::-1]

    def _finish(
        self,
        request_id: str,
        state: str,
        *,
        error: str | None = None,
        tokens: int = 0,
    ) -> RequestRecord:
        with self._lock:
            current = self._records.get(request_id)
            if current is None:
                raise KeyError(f"unknown request: {request_id}")
            if current.state != _ACTIVE:
                return current
            updated = RequestRecord(
                current.request_id,
                current.model_id,
                current.runtime_name,
                state,
                current.created_at,
                self._now(),
                error,
                max(0, tokens),
            )
            self._records[request_id] = updated
            self._persist(updated)
            return updated

    def _trim(self) -> None:
        excess = len(self._records) - self.max_records
        if excess > 0:
            for request_id in list(self._records)[:excess]:
                del self._records[request_id]

    def _load(self) -> None:
        if self.journal_path is None or not self.journal_path.exists():
            return
        with self.journal_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    record = RequestRecord(**value)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                self._records[record.request_id] = record
        recovered: list[RequestRecord] = []
        for request_id, record in list(self._records.items()):
            if record.state == _ACTIVE:
                updated = RequestRecord(
                    record.request_id,
                    record.model_id,
                    record.runtime_name,
                    _FAILED,
                    record.created_at,
                    self._now(),
                    _RECOVERY_ERROR,
                    record.tokens,
                )
                self._records[request_id] = updated
                recovered.append(updated)
        self.recovered_count = len(recovered)
        self._trim()
        for record in recovered:
            self._persist(record)

    def _persist(self, record: RequestRecord) -> None:
        if self.journal_path is None:
            return
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), separators=(",", ":"), sort_keys=True) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
