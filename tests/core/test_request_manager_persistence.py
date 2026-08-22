from __future__ import annotations

import json

import pytest

from orbit.core.request_manager import RequestManager


def test_request_lifecycle_is_persisted(tmp_path) -> None:
    journal = tmp_path / "requests.jsonl"
    manager = RequestManager(journal_path=journal)

    manager.start("req-1", "model-a", "runtime-a")
    manager.complete("req-1", tokens=7)

    restored = RequestManager(journal_path=journal)
    record = restored.get("req-1")

    assert record is not None
    assert record.state == "completed"
    assert record.tokens == 7
    assert record.error is None


def test_active_request_is_recovered_as_failed(tmp_path) -> None:
    journal = tmp_path / "requests.jsonl"
    manager = RequestManager(journal_path=journal)
    manager.start("req-1", "model-a", "runtime-a")

    restored = RequestManager(journal_path=journal)
    record = restored.get("req-1")

    assert record is not None
    assert record.state == "failed"
    assert record.error == "request interrupted by process restart"
    assert record.completed_at is not None


def test_recovery_ignores_blank_and_corrupt_lines(tmp_path) -> None:
    journal = tmp_path / "requests.jsonl"
    journal.write_text("\nnot-json\n" + json.dumps({"request_id": "req-1"}) + "\n", encoding="utf-8")

    restored = RequestManager(journal_path=journal)

    assert restored.recent() == []


def test_journal_rejects_non_positive_capacity() -> None:
    with pytest.raises(ValueError, match="max_records"):
        RequestManager(max_records=0)
