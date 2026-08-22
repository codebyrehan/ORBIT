from __future__ import annotations

from pathlib import Path

from orbit.core.recovery import RecoveryManager
from orbit.core.request_manager import RequestManager


def test_recovery_manager_reports_interrupted_requests(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    manager = RequestManager(journal_path=journal)
    manager.start("req-1", "model-a", "runtime-a")
    manager.complete("req-1", tokens=4)
    manager.start("req-2", "model-a", "runtime-a")

    recovered, report = RecoveryManager(tmp_path).recover_requests()

    assert recovered.get("req-1") is not None
    assert recovered.get("req-1").state == "completed"
    assert recovered.get("req-2").state == "failed"
    assert report.recovered_requests == 1
    assert report.active_requests == 0
    assert report.failed_requests == 1


def test_recovery_ignores_corrupt_journal_lines(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    journal.write_text("not-json\n\n", encoding="utf-8")

    manager, report = RecoveryManager(tmp_path).recover_requests()

    assert manager.recent() == []
    assert report.recovered_requests == 0
    assert report.failed_requests == 0
