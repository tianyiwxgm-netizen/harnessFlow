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


# ---------------------------------------------------------------------------
# TC-E14 · query_by_tick · 其它 project 查询 · raise CROSS_PROJECT
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E14_query_by_tick_cross_project_raises(
    sut, mock_project_id, make_audit_cmd
) -> None:
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-e14",
        reason="owner", evidence=["e1"],
    ))
    with pytest.raises(AuditError) as exc:
        sut.query_by_tick(
            tick_id="tick-e14",
            project_id="pid-not-owner",
            include_buffered=True,
        )
    assert exc.value.error_code == E_AUDIT_CROSS_PROJECT


# ---------------------------------------------------------------------------
# TC-E15 · flush 空 buffer · count=0 · event_bus 未被调用
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E15_flush_empty_buffer_noop(
    sut, mock_event_bus
) -> None:
    fr = sut.flush_buffer(force=True, reason="tick_boundary")
    assert fr.flushed_count == 0
    assert fr.last_event_id is None
    assert fr.last_hash == "0" * 64
    mock_event_bus.append_event.assert_not_called()
    assert sut.current_state() == "buffering"
