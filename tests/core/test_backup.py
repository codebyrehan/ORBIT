from __future__ import annotations

import json
from pathlib import Path

from orbit.core.backup import create_request_backup, restore_request_backup


def test_backup_filters_corrupt_lines_and_writes_atomically(tmp_path: Path) -> None:
    journal = tmp_path / "requests.jsonl"
    backup = tmp_path / "backup.jsonl"
    journal.write_text(
        json.dumps({"request_id": "r1", "state": "completed"}) + "\n"
        "not-json\n"
        + json.dumps({"request_id": "r2", "state": "failed"})
        + "\n",
        encoding="utf-8",
    )

    assert create_request_backup(journal, backup) == backup
    lines = backup.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["request_id"] == "r1"
    assert json.loads(lines[1])["request_id"] == "r2"


def test_restore_replaces_destination_with_validated_snapshot(tmp_path: Path) -> None:
    backup = tmp_path / "backup.jsonl"
    journal = tmp_path / "requests.jsonl"
    backup.write_text(json.dumps({"request_id": "r1", "state": "failed"}) + "\n", encoding="utf-8")
    journal.write_text(json.dumps({"request_id": "old", "state": "active"}) + "\n", encoding="utf-8")

    restore_request_backup(backup, journal)

    assert '"r1"' in journal.read_text(encoding="utf-8")
    assert '"old"' not in journal.read_text(encoding="utf-8")
