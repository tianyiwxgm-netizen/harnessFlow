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


# ---------------------------------------------------------------------------
# TC-E16 · _captured_events 钩子 · flush 后内含 hash+sequence+audit_id
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E16_captured_events_hook_exposes_flush_meta(
    sut, mock_project_id, make_audit_cmd
) -> None:
    for i in range(2):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-e16-{i}",
            reason=f"r{i}", evidence=[f"e{i}"],
        ))
    assert sut._captured_events == []  # flush 前为空
    sut.flush_buffer(force=True, reason="tick_boundary")
    captured = sut._captured_events
    assert len(captured) == 2
    assert captured[0]["sequence"] == 1
    assert captured[1]["sequence"] == 2
    # 第 2 条 prev = 第 1 条 hash(链式)
    assert captured[1]["prev_hash"] == captured[0]["hash"]
    assert all("audit_id" in c and len(c["hash"]) == 64 for c in captured)


# ---------------------------------------------------------------------------
# TC-E17 · replay · max_entries=1 停早 · partial=True
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E17_replay_max_entries_stops_early_partial(
    make_recorder, mock_project_id, pre_populated_jsonl_dir
) -> None:
    rec = make_recorder(
        session_active_pid=mock_project_id,
        jsonl_root=pre_populated_jsonl_dir,
    )
    rr = rec.replay_from_jsonl(project_id=mock_project_id, max_entries=1)
    assert rr.replayed_count == 1
    assert rr.partial is True
    assert rec.replay_status() == "partial"


# ---------------------------------------------------------------------------
# TC-E18 · replay · 损坏 hash 链 · hash_chain_valid=False + first_broken_at
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E18_replay_detects_corrupted_hash_chain(
    make_recorder, mock_project_id, corrupted_jsonl_dir
) -> None:
    rec = make_recorder(
        session_active_pid=mock_project_id,
        jsonl_root=corrupted_jsonl_dir,
    )
    rr = rec.replay_from_jsonl(project_id=mock_project_id)
    assert rr.hash_chain_valid is False
    assert rr.first_broken_at is not None
    assert "seq" in rr.first_broken_at


# ---------------------------------------------------------------------------
# TC-E19 · replay · from_date 过滤 · 只扫新文件
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E19_replay_from_date_skips_older_files(
    make_recorder, mock_project_id, pre_populated_jsonl_dir
) -> None:
    # pre_populated_jsonl_dir 只有 2026-04-20 单文件 · from_date=2026-04-30 应跳过
    rec = make_recorder(
        session_active_pid=mock_project_id,
        jsonl_root=pre_populated_jsonl_dir,
    )
    rr = rec.replay_from_jsonl(
        project_id=mock_project_id, from_date="2026-04-30"
    )
    assert rr.replayed_count == 0
    assert rr.files_scanned == 0
    assert rec.replay_status() == "complete"


# ---------------------------------------------------------------------------
# TC-E20 · query_by_tick · max_results 截断 · 10 条入 · max=3
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E20_query_by_tick_max_results_truncates(
    sut, mock_project_id, make_audit_cmd
) -> None:
    for i in range(5):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-e20",
            reason=f"r{i}", evidence=[f"e{i}"],
        ))
    r = sut.query_by_tick(
        tick_id="tick-e20",
        project_id=mock_project_id,
        include_buffered=True,
        max_results=3,
    )
    assert r.count == 3
    assert len(r.entries) == 3
    assert r.source == "buffer"


# ---------------------------------------------------------------------------
# TC-E21 · recent_meta entries 携 error_code + level · reason 拒绝场景
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E21_recent_meta_carries_error_code_and_level(
    sut, mock_project_id, make_audit_cmd
) -> None:
    with pytest.raises(AuditError):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick="tick-e21",
            reason="   ", evidence=["e1"],  # 空白 reason
        ))
    metas = sut.get_recent_audits()
    assert len(metas) == 1
    m = metas[0]
    assert m.action == "audit_rejected"
    assert m.level == "WARN"
    assert m.error_code is not None and m.error_code.startswith("E_AUDIT_")
    assert m.event_type == "L1-01:audit_rejected"


# ---------------------------------------------------------------------------
# TC-E22 · query_by_decision · 其它 project 查询 · raise CROSS_PROJECT
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E22_query_by_decision_cross_project_raises(
    sut, mock_project_id, make_audit_cmd
) -> None:
    sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="decision_made",
        actor={"l1": "L1-01", "l2": "L2-02"},
        project_id=mock_project_id,
        linked_decision="dec-e22",
        reason="owner decision", evidence=["e1"],
        payload={"decision_type": "invoke_skill"},
    ))
    with pytest.raises(AuditError) as exc:
        sut.query_by_decision(
            decision_id="dec-e22", project_id="pid-other-team"
        )
    assert exc.value.error_code == E_AUDIT_CROSS_PROJECT


# ---------------------------------------------------------------------------
# TC-E23 · get_hash_tip · 多批 flush 后 sequence 累加 · hash 变更
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E23_get_hash_tip_sequence_accumulates(
    sut, mock_project_id, make_audit_cmd
) -> None:
    tip0 = sut.get_hash_tip(project_id=mock_project_id)
    assert tip0.sequence == 0
    assert tip0.hash == "0" * 64
    for batch in range(3):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-e23-{batch}",
            reason=f"r{batch}", evidence=[f"e{batch}"],
        ))
        sut.flush_buffer(force=True, reason="tick_boundary")
    tip = sut.get_hash_tip(project_id=mock_project_id)
    assert tip.sequence == 3
    assert tip.hash != "0" * 64
    assert len(tip.hash) == 64


# ---------------------------------------------------------------------------
# TC-E24 · event_bus.append_event · links 含 audit_id · idempotency_key 回退
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E24_append_event_has_audit_link_and_fallback_idempotency(
    sut, mock_project_id, mock_event_bus, make_audit_cmd
) -> None:
    r = sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-e24",
        reason="link check", evidence=["e1"],
        # idempotency_key 留空 · 观察是否 fallback 到 audit_id
    ))
    sut.flush_buffer(force=True, reason="tick_boundary")
    call = mock_event_bus.append_event.call_args_list[0]
    links = call.kwargs.get("links") or []
    assert any(
        isinstance(l, dict) and l.get("kind") == "audit" and l.get("ref") == r.audit_id
        for l in links
    )
    # idempotency_key fallback = audit_id
    assert call.kwargs.get("idempotency_key") == r.audit_id
