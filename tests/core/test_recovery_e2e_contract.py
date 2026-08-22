from __future__ import annotations

import json
from pathlib import Path

from orbit.core.recovery import RecoveryManager


def test_recovery_contract_marks_only_active_records_as_recovered(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    records = [
        {"request_id": "active", "model_id": "m", "runtime_name": "cpu", "state": "active", "created_at": "2026-01-01T00:00:00+00:00", "completed_at": None, "error": None, "tokens": 0},
        {"request_id": "done", "model_id": "m", "runtime_name": "cpu", "state": "completed", "created_at": "2026-01-01T00:00:00+00:00", "completed_at": "2026-01-01T00:00:01+00:00", "error": None, "tokens": 1},
    ]
    journal.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")

    manager, report = RecoveryManager(tmp_path).recover_requests()

    assert report.recovered_requests == 1
    assert manager.get("active") is not None
    assert manager.get("active").state == "failed"
    assert manager.get("done").state == "completed"
