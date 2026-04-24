"""L2-05 负向用例 · §11.1 10 项 E_AUDIT_* 全覆盖 + FLUSH_CONCURRENT.

对齐 3-2 §3 · TC-L101-L205-101~111 + 108b.
"""
from __future__ import annotations

import threading

import pytest

from app.main_loop.decision_audit.errors import AuditError


# ---------------------------------------------------------------------------
# record_audit 侧错误码
# ---------------------------------------------------------------------------


def test_TC_L101_L205_106_no_project_id_rejected(sut, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=None, linked_tick="tick-001",
        reason="no pid", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_NO_PROJECT_ID"


def test_TC_L101_L205_107_no_reason_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_NO_REASON"
    meta = [a for a in sut.get_recent_audits() if a.event_type == "L1-01:audit_rejected"]
    assert len(meta) >= 1


def test_TC_L101_L205_108_cross_project_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    sut._register_tick("tick-other-pid", project_id="pid-OTHER-018f4a3b-9999-7000-FFFF")
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-other-pid",
        reason="wrong pid", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_CROSS_PROJECT"


def test_TC_L101_L205_109_unknown_event_type_rejected(sut, mock_project_id, make_audit_cmd) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="frobnicate_the_widget",
        project_id=mock_project_id, linked_tick="tick-001",
        reason="invalid action", evidence=["evt-1"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_EVENT_TYPE_UNKNOWN"


def test_TC_L101_L205_105_halt_on_fail_rejects_silently(sut, mock_project_id, make_audit_cmd) -> None:
    sut._force_halted()
    cmd = make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-after-halt",
        reason="should be rejected", evidence=["evt-x"],
    )
    with pytest.raises(AuditError) as exc:
        sut.record_audit(cmd)
    assert exc.value.error_code == "E_AUDIT_HALT_ON_FAIL"
    assert sut.buffer_size() == 0


def test_TC_L101_L205_110_stale_buffer_force_flush_and_warn(sut, mock_project_id, make_audit_cmd) -> None:
    tick_a = "tick-stale-A"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_a,
        reason="stale buffer fixture", evidence=["evt-a"],
    ))
    tick_b = "tick-next-B"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_b,
        reason="next tick", evidence=["evt-b"],
    ))
    warns = [a for a in sut.get_recent_audits() if a.error_code == "E_AUDIT_STALE_BUFFER"]
    assert len(warns) == 1
    from_index = sut.query_by_tick(tick_id=tick_a, project_id=mock_project_id, include_buffered=False)
    assert from_index.count >= 1
