"""In-process observability metrics for the ORBIT control plane."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    requests_started: int
    requests_completed: int
    requests_failed: int
    requests_cancelled: int
    tokens_total: int
    failovers_total: int
    latency_ms_total: float


class MetricsRegistry:
    """Thread-safe counters with no request-content retention."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._tokens = 0
        self._failovers = 0
        self._latency_ms = 0.0
        self._started_at: dict[str, float] = {}

    def request_started(self, request_id: str) -> None:
        with self._lock:
            self._started += 1
            self._started_at[request_id] = monotonic()

    def request_completed(self, request_id: str, tokens: int = 0) -> None:
        self._finish(request_id, "completed", tokens)

    def request_failed(self, request_id: str, tokens: int = 0) -> None:
        self._finish(request_id, "failed", tokens)

    def request_cancelled(self, request_id: str) -> None:
        self._finish(request_id, "cancelled", 0)

    def failover(self) -> None:
        with self._lock:
            self._failovers += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(self._started, self._completed, self._failed, self._cancelled, self._tokens, self._failovers, self._latency_ms)

    def _finish(self, request_id: str, state: str, tokens: int) -> None:
        with self._lock:
            started = self._started_at.pop(request_id, None)
            if started is not None:
                self._latency_ms += (monotonic() - started) * 1000.0
            self._tokens += max(0, tokens)
            if state == "completed":
                self._completed += 1
            elif state == "failed":
                self._failed += 1
            else:
                self._cancelled += 1
