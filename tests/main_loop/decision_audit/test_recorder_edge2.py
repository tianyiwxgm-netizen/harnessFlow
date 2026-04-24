"""L2-05 recorder 收尾 TC · WP01 · TC-E13-E24.

覆盖 recorder.py 剩余主入口/集成路径:
    - traceability 集成 (decision_made → mark_audited)
    - replay 高级 (from_date / max_entries / 损坏链 / timeout)
    - query cross_project / max_results
    - captured_events hook / recent_meta levels
    - flush empty-buffer short-circuit
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_audit import (
    AuditError,
    E_AUDIT_CROSS_PROJECT,
)


# ---------------------------------------------------------------------------
# TC-E13 · record_audit(decision_made) 自动登记+mark_audited · traceability 100%
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E13_decision_made_registers_and_marks_audited(
    sut, mock_project_id, make_audit_cmd
) -> None:
    """decision_made + linked_decision → traceability 完整登记+审计."""
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="decision_made",
        actor={"l1": "L1-01", "l2": "L2-02"},
        project_id=mock_project_id,
        linked_tick="tick-e13",
        linked_decision="dec-e13-001",
        reason="traceability integration",
        evidence=["e1"],
        payload={"decision_type": "invoke_skill"},
    ))
    assert sut.traceability.has_decision("dec-e13-001")
    assert sut.traceability.is_audited("dec-e13-001")
    rep = sut.traceability.report()
    assert rep.is_full_coverage
