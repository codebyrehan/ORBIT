import json
import logging

from orbit.observability import JsonFormatter, RequestTrace, RuntimeMetrics


def test_runtime_metrics_snapshot() -> None:
    metrics = RuntimeMetrics()
    metrics.record(latency_ms=100, tokens=20)
    metrics.record(latency_ms=50, tokens=10, failed=True)
    snapshot = metrics.snapshot()
    assert snapshot["requests_total"] == 2
    assert snapshot["requests_failed"] == 1
    assert snapshot["tokens_total"] == 30
    assert snapshot["latency_ms_avg"] == 75.0
    assert snapshot["error_rate"] == 0.5


def test_json_formatter_includes_request_id() -> None:
    record = logging.LogRecord("orbit", logging.INFO, "", 0, "started", (), None)
    record.request_id = "abc123"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["level"] == "INFO"
    assert payload["message"] == "started"
    assert payload["request_id"] == "abc123"


def test_request_trace_has_id_and_elapsed_time() -> None:
    trace = RequestTrace()
    assert trace.request_id
    assert trace.elapsed_ms >= 0
    assert trace.extra() == {"request_id": trace.request_id}
