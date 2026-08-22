"""Structured observability primitives for ORBIT."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4


@dataclass(slots=True)
class RuntimeMetrics:
    requests_total: int = 0
    requests_failed: int = 0
    tokens_total: int = 0
    latency_ms_total: float = 0.0

    def record(self, *, latency_ms: float, tokens: int, failed: bool = False) -> None:
        self.requests_total += 1
        self.requests_failed += int(failed)
        self.tokens_total += tokens
        self.latency_ms_total += latency_ms

    def snapshot(self) -> dict[str, float | int]:
        requests = self.requests_total
        return {
            "requests_total": requests,
            "requests_failed": self.requests_failed,
            "tokens_total": self.tokens_total,
            "latency_ms_total": round(self.latency_ms_total, 3),
            "latency_ms_avg": round(self.latency_ms_total / requests, 3) if requests else 0.0,
            "error_rate": self.requests_failed / requests if requests else 0.0,
        }


class JsonFormatter(logging.Formatter):
    """Render logs as stable JSON objects for local and production collectors."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


class RequestTrace:
    """Small request-scoped trace object for correlating runtime events."""

    def __init__(self, request_id: str | None = None) -> None:
        self.request_id = request_id or uuid4().hex
        self.started = monotonic()

    @property
    def elapsed_ms(self) -> float:
        return (monotonic() - self.started) * 1000

    def extra(self) -> dict[str, str]:
        return {"request_id": self.request_id}
