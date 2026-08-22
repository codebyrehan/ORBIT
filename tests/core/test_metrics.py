from __future__ import annotations

from orbit.core.metrics import MetricsRegistry


def test_metrics_track_request_lifecycle_and_tokens() -> None:
    metrics = MetricsRegistry()
    metrics.request_started("r1")
    metrics.request_completed("r1", tokens=12)
    metrics.request_started("r2")
    metrics.request_failed("r2", tokens=3)
    metrics.request_started("r3")
    metrics.request_cancelled("r3")
    metrics.failover()

    snapshot = metrics.snapshot()
    assert snapshot.requests_started == 3
    assert snapshot.requests_completed == 1
    assert snapshot.requests_failed == 1
    assert snapshot.requests_cancelled == 1
    assert snapshot.tokens_total == 15
    assert snapshot.failovers_total == 1
    assert snapshot.latency_ms_total >= 0


def test_metrics_do_not_retain_finished_request_ids() -> None:
    metrics = MetricsRegistry()
    metrics.request_started("secret-id")
    metrics.request_completed("secret-id")

    assert metrics.snapshot().requests_completed == 1
    assert not hasattr(metrics, "requests")
