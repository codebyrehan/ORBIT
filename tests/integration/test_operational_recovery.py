from __future__ import annotations

import json
from pathlib import Path

from orbit.core.recovery import RecoveryManager
from orbit.core.request_manager import RequestManager


def test_restart_reconciles_active_requests_to_failed(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    manager = RequestManager(journal_path=journal)
    manager.start("req-1", "model-a", "runtime-a")

    recovered, report = RecoveryManager(tmp_path).recover_requests()

    record = recovered.get("req-1")
    assert record is not None
    assert record.state == "failed"
    assert record.error == "request interrupted by process restart"
    assert report.recovered_requests == 1
    assert report.active_requests == 0
    assert report.failed_requests == 1


def test_restart_recovery_is_idempotent(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    manager = RequestManager(journal_path=journal)
    manager.start("req-1", "model-a", "runtime-a")

    first, first_report = RecoveryManager(tmp_path).recover_requests()
    second, second_report = RecoveryManager(tmp_path).recover_requests()

    assert first.get("req-1") == second.get("req-1")
    assert first_report.recovered_requests == 1
    assert second_report.recovered_requests == 0
    assert second_report.active_requests == 0


def test_recovery_ignores_truncated_and_invalid_journal_lines(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    valid = {
        "request_id": "req-1",
        "model_id": "model-a",
        "runtime_name": "runtime-a",
        "state": "completed",
        "created_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:00:01+00:00",
        "error": None,
        "tokens": 2,
    }
    journal.write_text(json.dumps(valid) + "\n{not-json\n{\"truncated\":", encoding="utf-8")

    manager, report = RecoveryManager(tmp_path).recover_requests()

    record = manager.get("req-1")
    assert record is not None
    assert record.state == "completed"
    assert report.recovered_requests == 0
    assert report.active_requests == 0


def test_unresolved_returns_only_active_records(tmp_path: Path) -> None:
    manager = RequestManager()
    manager.start("req-1", "model-a", "runtime-a")
    manager.complete("req-1", tokens=1)
    manager.start("req-2", "model-a", "runtime-a")

    unresolved = RecoveryManager.unresolved(manager)

    assert [record.request_id for record in unresolved] == ["req-2"]
