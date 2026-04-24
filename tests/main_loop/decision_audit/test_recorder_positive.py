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


# ---------------------------------------------------------------------------
# query_by_tick / by_decision / by_chain
# ---------------------------------------------------------------------------


def test_TC_L101_L205_007_query_by_tick_hits_buffer_includes_buffered(
    sut, mock_project_id, make_audit_cmd
) -> None:
    tick_id = "tick-018f4a3b-7c1e-7000-8b2a-5555555555ee"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_id,
        reason="event_bus_trigger", evidence=["evt-1"],
    ))
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="decision_made",
        actor={"l1": "L1-01", "l2": "L2-02"},
        project_id=mock_project_id, linked_tick=tick_id, linked_decision="dec-001",
        reason="选择 invoke_skill 因 KB 命中且 reason 达到 20 字",
        evidence=["evt-2"], payload={"decision_type": "invoke_skill"},
    ))
    result = sut.query_by_tick(tick_id=tick_id, project_id=mock_project_id, include_buffered=True)
    assert result.count == 2
    assert result.source in ("buffer", "mixed")
    actions = [e.action for e in result.entries]
    assert "tick_scheduled" in actions and "decision_made" in actions


def test_TC_L101_L205_008_query_by_tick_mixed_buffer_and_index_after_flush(
    sut, mock_project_id, make_audit_cmd
) -> None:
    tick_id = "tick-018f4a3b-7c1e-7000-8b2a-6666666666ff"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick=tick_id,
        reason="flushed first", evidence=["evt-1"],
    ))
    sut.flush_buffer(force=True, reason="tick_boundary")
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_completed",
        project_id=mock_project_id, linked_tick=tick_id,
        reason="late buffered", evidence=["evt-2"],
    ))
    result = sut.query_by_tick(tick_id=tick_id, project_id=mock_project_id, include_buffered=True)
    assert result.count == 2
    assert result.source == "mixed"


def test_TC_L101_L205_009_query_by_decision_returns_single_entry(
    sut, mock_project_id, make_audit_cmd
) -> None:
    decision_id = "dec-018f4a3b-7c1e-7000-8b2a-7777777777aa"
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="decision_made",
        actor={"l1": "L1-01", "l2": "L2-02"},
        project_id=mock_project_id, linked_decision=decision_id,
        reason="decision 单条反查 · reason 长度足以满足 20 字最小要求",
        evidence=["evt-dec-001"], payload={"decision_type": "invoke_skill"},
    ))
    entry = sut.query_by_decision(decision_id=decision_id, project_id=mock_project_id)
    assert entry is not None
    assert entry.linked_decision == decision_id
    assert entry.action == "decision_made"


def test_TC_L101_L205_010_query_by_chain_returns_multiple_entries(
    sut, mock_project_id, make_audit_cmd
) -> None:
    chain_id = "ch-018f4a3b-7c1e-7000-8b2a-8888888888bb"
    for i in range(3):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-07", action="chain_step_completed",
            actor={"l1": "L1-01", "l2": "L2-04"},
            project_id=mock_project_id, linked_chain=chain_id,
            reason=f"step {i + 1} ok", evidence=[f"evt-step-{i}"],
            payload={"chain_id": chain_id, "step_id": f"step-{i + 1}"},
        ))
    entries = sut.query_by_chain(chain_id=chain_id, project_id=mock_project_id)
    assert len(entries) == 3
    assert all(e.linked_chain == chain_id for e in entries)


# ---------------------------------------------------------------------------
# flush_buffer / hash_tip
# ---------------------------------------------------------------------------


def test_TC_L101_L205_011_flush_buffer_tick_boundary_ok(
    sut, mock_project_id, mock_event_bus, make_audit_cmd
) -> None:
    for i in range(5):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-{i}",
            reason=f"trigger {i}", evidence=[f"evt-{i}"],
        ))
    fr = sut.flush_buffer(force=True, reason="tick_boundary")
    assert fr.flushed_count == 5
    assert fr.last_event_id is not None
    assert fr.last_hash and len(fr.last_hash) == 64
    assert fr.duration_ms <= 50
    assert mock_event_bus.append_event.call_count == 5


def test_TC_L101_L205_012_flush_buffer_empty_is_noop(sut, mock_event_bus) -> None:
    fr = sut.flush_buffer(force=True, reason="tick_boundary")
    assert fr.flushed_count == 0
    assert fr.last_event_id is None
    assert mock_event_bus.append_event.call_count == 0


def test_TC_L101_L205_014_get_hash_tip_genesis_is_all_zero(sut, mock_project_id) -> None:
    tip = sut.get_hash_tip(project_id=mock_project_id)
    assert tip.hash == "0" * 64
    assert tip.sequence == 0


def test_TC_L101_L205_015_get_hash_tip_after_flush_increments(
    sut, mock_project_id, make_audit_cmd
) -> None:
    for i in range(3):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-{i}",
            reason=f"trigger {i}", evidence=[f"evt-{i}"],
        ))
    sut.flush_buffer(force=True, reason="tick_boundary")
    tip = sut.get_hash_tip(project_id=mock_project_id)
    assert tip.sequence == 3
    assert tip.hash != "0" * 64


# ---------------------------------------------------------------------------
# replay_from_jsonl · TC-013 (fixture 驱动)
# ---------------------------------------------------------------------------


def test_TC_L101_L205_013_replay_rebuilds_reverse_index(
    make_recorder, jsonl_fixture_file, mock_project_id
) -> None:
    # 构造一个指向 jsonl_root(tmp_path)的 recorder
    # jsonl_path:tmp_path/projects/<pid>/audit/l1-01/<file>.jsonl · parents[4] = tmp_path
    jsonl_root = jsonl_fixture_file.parents[4]
    rec = make_recorder(session_active_pid=mock_project_id, jsonl_root=jsonl_root)
    rr = rec.replay_from_jsonl(
        project_id=mock_project_id,
        from_date="2026-04-15",
        max_entries=100_000,
    )
    assert rr.replayed_count >= 3
    assert rr.hash_chain_valid is True
    assert rr.latest_hash and len(rr.latest_hash) == 64
    tip = rec.get_hash_tip(project_id=mock_project_id)
    assert tip.hash == rr.latest_hash
    assert tip.sequence == rr.replayed_count
