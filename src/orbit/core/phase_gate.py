"""Small, dependency-free release gate helpers used by automation and tests."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GateResult:
    name: str
    passed: bool
    detail: str = ""


def require_all(results: list[GateResult]) -> None:
    """Raise a concise error when any release gate has failed."""
    failed = [r for r in results if not r.passed]
    if failed:
        summary = "; ".join(f"{r.name}: {r.detail or 'failed'}" for r in failed)
        raise RuntimeError(f"release gate failed: {summary}")
