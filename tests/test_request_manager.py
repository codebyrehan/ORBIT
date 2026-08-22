import pytest

from orbit.core.request_manager import RequestManager


def test_request_manager_tracks_completion_and_bounds_history() -> None:
    manager = RequestManager(max_records=2)
    manager.start("r1", "m1", "rt1")
    completed = manager.complete("r1", tokens=3)
    manager.start("r2", "m1", "rt1")
    manager.start("r3", "m2", "rt2")

    assert completed.state == "completed"
    assert completed.tokens == 3
    assert manager.get("r1") is None
    assert [item.request_id for item in manager.recent()] == ["r3", "r2"]


def test_request_manager_failure_and_cancel() -> None:
    manager = RequestManager()
    manager.start("r1", "m1", "rt1")
    failed = manager.fail("r1", "boom", tokens=2)
    assert failed.state == "failed"
    assert failed.error == "boom"
    assert manager.cancel("r1").state == "failed"


def test_request_manager_rejects_unknown_and_invalid_limits() -> None:
    manager = RequestManager(max_records=2)
    with pytest.raises(KeyError):
        manager.complete("missing")
    with pytest.raises(ValueError):
        manager.recent(0)
    with pytest.raises(ValueError):
        RequestManager(0)
