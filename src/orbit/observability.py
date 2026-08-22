"""Structured observability primitives for ORBIT."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from uuid import uuid4
import json
import logging


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

    def prometheus(self) -> str:
        """Render metrics in dependency-free Prometheus text format."""
        snapshot = self.snapshot()
        lines = [
            "# HELP orbit_requests_total Total completed inference requests.",
            "# TYPE orbit_requests_total counter",
            f"orbit_requests_total {snapshot['requests_total']}",
            "# HELP orbit_requests_failed_total Total failed inference requests.",
            "# TYPE orbit_requests_failed_total counter",
            f"orbit_requests_failed_total {snapshot['requests_failed']}",
            "# HELP orbit_tokens_total Total generated tokens recorded by ORBIT.",
            "# TYPE orbit_tokens_total counter",
            f"orbit_tokens_total {snapshot['tokens_total']}",
            "# HELP orbit_latency_ms_total Total inference latency in milliseconds.",
            "# TYPE orbit_latency_ms_total counter",
            f"orbit_latency_ms_total {snapshot['latency_ms_total']}",
            "# HELP orbit_latency_ms_avg Average recorded inference latency in milliseconds.",
            "# TYPE orbit_latency_ms_avg gauge",
            f"orbit_latency_ms_avg {snapshot['latency_ms_avg']}",
            "# HELP orbit_error_rate Fraction of recorded requests that failed.",
            "# TYPE orbit_error_rate gauge",
            f"orbit_error_rate {snapshot['error_rate']}",
        ]
        return "\n".join(lines) + "\n"


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
