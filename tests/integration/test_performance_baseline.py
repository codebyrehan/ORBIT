from __future__ import annotations

from time import perf_counter

from orbit.observability import RuntimeMetrics


def test_metrics_recording_is_fast_enough_for_request_hot_path() -> None:
    metrics = RuntimeMetrics()
    start = perf_counter()
    for _ in range(10_000):
        metrics.record(latency_ms=1.0, tokens=4)
    elapsed = perf_counter() - start

    assert metrics.requests_total == 10_000
    assert metrics.tokens_total == 40_000
    assert elapsed < 0.25


def test_prometheus_export_remains_bounded() -> None:
    metrics = RuntimeMetrics()
    for _ in range(10_000):
        metrics.record(latency_ms=1.0, tokens=4)

    payload = metrics.prometheus()
    assert len(payload) < 4_096
    assert "orbit_requests_total 10000" in payload
