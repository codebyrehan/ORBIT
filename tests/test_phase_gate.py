import pytest

from orbit.core.phase_gate import GateResult, require_all


def test_require_all_accepts_passing_gates():
    require_all([GateResult("health", True), GateResult("runtime", True)])


def test_require_all_reports_failed_gates():
    with pytest.raises(RuntimeError, match="runtime: provider unavailable"):
        require_all([GateResult("health", True), GateResult("runtime", False, "provider unavailable")])
