from pathlib import Path

from orbit.audit import AuditLog


def test_audit_log_records_and_reads_recent_events(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")

    event = log.record(
        request_id="req-1",
        method="GET",
        path="/v1/models",
        status_code=200,
        duration_ms=3.14159,
        authenticated=True,
    )
    log.record(
        request_id="req-2",
        method="POST",
        path="/v1/chat/completions",
        status_code=429,
        duration_ms=1.0,
        authenticated=False,
    )

    assert event.request_id == "req-1"
    assert len(log.recent(1)) == 1
    assert log.recent(1)[0]["request_id"] == "req-2"
    assert log.recent(10)[1]["request_id"] == "req-1"


def test_audit_log_does_not_store_request_headers_or_body(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(request_id="req-secret", method="POST", path="/v1/chat/completions", status_code=200, duration_ms=1.0, authenticated=True)

    raw = log.path.read_text(encoding="utf-8")

    assert "authorization" not in raw.lower()
    assert "password" not in raw.lower()
    assert "content" not in raw.lower()


def test_audit_log_rejects_invalid_limits(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")

    for limit in (0, 1001):
        try:
            log.recent(limit)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid audit limit was accepted")
