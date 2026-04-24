"""L2-05 正向用例 · record_audit / query_by_* / flush / replay / hash_tip.

对齐 3-2 §2 · TC-L101-L205-001 ~ 015.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# TC-001 · record_audit decision_made
# ---------------------------------------------------------------------------


def test_TC_L101_L205_001_record_audit_decision_made_returns_audit_id(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05",
        actor={"l1": "L1-01", "l2": "L2-02"},
        action="decision_made",
        project_id=mock_project_id,
        linked_decision="dec-018f4a3b-7c1e-7000-8b2a-1111111111aa",
        reason="选择 invoke_skill: tdd.blueprint_generate 因 KB 命中 5 条相似且 evidence 充分",
        evidence=["evt-kb-001", "evt-5dis-002"],
        payload={"decision_type": "invoke_skill"},
    )
    result = sut.record_audit(cmd)
    assert result.audit_id.startswith("audit-")
    assert result.buffered is True
    assert result.buffer_remaining == 63
    assert result.event_id is None


def test_TC_L101_L205_002_record_audit_tick_scheduled_from_l2_01(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05",
        actor={"l1": "L1-01", "l2": "L2-01"},
        action="tick_scheduled",
        project_id=mock_project_id,
        linked_tick="tick-018f4a3b-7c1e-7000-8b2a-2222222222bb",
        reason="event_bus_trigger",
        evidence=["evt-bus-001"],
    )
    r = sut.record_audit(cmd)
    assert r.buffered is True
    buf = sut.peek_buffer()
    assert buf[-1].action == "tick_scheduled"
    assert buf[-1].linked_tick == cmd.linked_tick


def test_TC_L101_L205_003_record_audit_state_transitioned_via_ic_l2_06(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-06",
        actor={"l1": "L1-01", "l2": "L2-03"},
        action="state_transitioned",
        project_id=mock_project_id,
        reason="tick 触发 S3→S4 转换 · allowed_next 通过",
        evidence=["evt-trans-001"],
        payload={"from_state": "S3", "to_state": "S4", "accepted": True},
    )
    r = sut.record_audit(cmd)
    assert r.buffered is True
    assert sut.peek_buffer()[-1].source_ic == "IC-L2-06"


def test_TC_L101_L205_004_record_audit_chain_step_via_ic_l2_07(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-07",
        actor={"l1": "L1-01", "l2": "L2-04"},
        action="chain_step_completed",
        project_id=mock_project_id,
        linked_chain="ch-018f4a3b-7c1e-7000-8b2a-3333333333cc",
        reason="step 2/5 ok",
        evidence=["evt-step-001"],
        payload={"chain_id": "ch-...", "step_id": "step-2", "outcome": "success"},
    )
    r = sut.record_audit(cmd)
    assert r.buffered is True
    assert sut.peek_buffer()[-1].linked_chain.startswith("ch-")


def test_TC_L101_L205_005_record_audit_warn_response_via_ic_l2_09(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-09",
        actor={"l1": "L1-01", "l2": "L2-02"},
        action="warn_response",
        project_id=mock_project_id,
        linked_warn="warn-018f4a3b-7c1e-7000-8b2a-4444444444dd",
        reason="接受 supervisor WARN: 建议补充 KB 检索，已补充",
        evidence=["evt-warn-001"],
        payload={"response": "accept"},
    )
    r = sut.record_audit(cmd)
    assert r.buffered is True


def test_TC_L101_L205_006_record_audit_idempotency_key_returns_same_audit_id(
    sut, mock_project_id, make_audit_cmd
) -> None:
    cmd = make_audit_cmd(
        source_ic="IC-L2-05",
        actor={"l1": "L1-01", "l2": "L2-01"},
        action="tick_scheduled",
        project_id=mock_project_id,
        linked_tick="tick-idem-001",
        reason="event_bus_trigger",
        evidence=["evt-idem-001"],
        idempotency_key="evt-idem-001",
    )
    r1 = sut.record_audit(cmd)
    r2 = sut.record_audit(cmd)
    assert r1.audit_id == r2.audit_id
    assert sut.buffer_size() == 1
