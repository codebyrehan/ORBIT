from __future__ import annotations

from orbit.observability import RuntimeMetrics


def test_prometheus_export_is_valid_and_matches_snapshot() -> None:
    metrics = RuntimeMetrics()
    metrics.record(latency_ms=12.5, tokens=7)
    metrics.record(latency_ms=7.5, tokens=3, failed=True)

    snapshot = metrics.snapshot()
    payload = metrics.prometheus()

    assert "# TYPE orbit_requests_total counter" in payload
    assert "orbit_requests_total 2" in payload
    assert "orbit_requests_failed_total 1" in payload
    assert "orbit_tokens_total 10" in payload
    assert f"orbit_latency_ms_total {snapshot['latency_ms_total']}" in payload
    assert f"orbit_latency_ms_avg {snapshot['latency_ms_avg']}" in payload
    assert f"orbit_error_rate {snapshot['error_rate']}" in payload
    assert payload.endswith("\n")


def test_prometheus_export_is_empty_state_safe() -> None:
    payload = RuntimeMetrics().prometheus()

    assert "orbit_requests_total 0" in payload
    assert "orbit_latency_ms_avg 0.0" in payload
    assert "orbit_error_rate 0.0" in payload
