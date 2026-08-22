"""Crash-recovery reconciliation for ORBIT's durable control-plane state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orbit.core.request_manager import RequestManager, RequestRecord


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    recovered_requests: int
    active_requests: int
    failed_requests: int


class RecoveryManager:
    """Reconcile durable request state before accepting new work."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def recover_requests(self, *, max_records: int = 1000) -> tuple[RequestManager, RecoveryReport]:
        manager = RequestManager(max_records=max_records, journal_path=self.data_dir / "requests.jsonl")
        records = manager.recent(max_records)
        active = [record for record in records if record.state == "active"]
        failed = [record for record in records if record.state == "failed"]
        return manager, RecoveryReport(manager.recovered_count, len(active), len(failed))

    @staticmethod
    def unresolved(manager: RequestManager) -> list[RequestRecord]:
        return [record for record in manager.recent(manager.max_records) if record.state == "active"]
