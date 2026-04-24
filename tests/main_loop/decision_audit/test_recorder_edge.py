"""L2-05 边界 TC · WP01 收尾补充 10-12 项.

覆盖 recorder.py 主入口 edge paths:
    - query_by_decision / query_by_chain not-found
    - buffer_remaining / peek_buffer 语义
    - replay 各种 edge(no_data / max_entries / corrupted)
    - hash_tip 多项目独立
    - traceability 集成
"""
from __future__ import annotations

import pytest

from app.main_loop.decision_audit import AuditError, DecisionAuditRecorder


# ---------------------------------------------------------------------------
# TC-E01 · query_by_decision 未命中返 None(非异常)
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E01_query_by_decision_miss_returns_none(
    sut, mock_project_id
) -> None:
    entry = sut.query_by_decision(
        decision_id="dec-never-existed", project_id=mock_project_id
    )
    assert entry is None


# ---------------------------------------------------------------------------
# TC-E02 · query_by_chain 未命中返空 list(非异常)
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E02_query_by_chain_miss_returns_empty_list(
    sut, mock_project_id
) -> None:
    entries = sut.query_by_chain(
        chain_id="ch-never-existed", project_id=mock_project_id
    )
    assert entries == []


# ---------------------------------------------------------------------------
# TC-E03 · query_by_tick 未命中 · source=not_found + count=0
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E03_query_by_tick_miss_source_not_found(
    sut, mock_project_id
) -> None:
    result = sut.query_by_tick(
        tick_id="tick-never-existed",
        project_id=mock_project_id,
        include_buffered=True,
    )
    assert result.count == 0
    assert result.entries == []
    assert result.source == "not_found"


# ---------------------------------------------------------------------------
# TC-E04 · buffer_remaining 随 record_audit 递减
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E04_buffer_remaining_decrements_per_record(
    sut, mock_project_id, make_audit_cmd
) -> None:
    r1 = sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-buf-01",
        reason="first", evidence=["e1"],
    ))
    r2 = sut.record_audit(make_audit_cmd(
        source_ic="IC-L2-05", action="tick_scheduled",
        project_id=mock_project_id, linked_tick="tick-buf-02",
        reason="second", evidence=["e2"],
    ))
    assert r1.buffer_remaining == 63
    assert r2.buffer_remaining == 62
    assert sut.buffer_size() == 2


# ---------------------------------------------------------------------------
# TC-E05 · flush 后 buffer 清空 · state 回 buffering
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E05_flush_clears_buffer_and_restores_state(
    sut, mock_project_id, make_audit_cmd
) -> None:
    for i in range(3):
        sut.record_audit(make_audit_cmd(
            source_ic="IC-L2-05", action="tick_scheduled",
            project_id=mock_project_id, linked_tick=f"tick-e05-{i}",
            reason=f"r{i}", evidence=[f"e{i}"],
        ))
    assert sut.buffer_size() == 3
    sut.flush_buffer(force=True, reason="tick_boundary")
    assert sut.buffer_size() == 0
    assert sut.current_state() == "buffering"


# ---------------------------------------------------------------------------
# TC-E06 · replay no_root · replay_status 更新 + genesis 返回
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E06_replay_without_jsonl_root_sets_status_no_root(
    sut, mock_project_id
) -> None:
    # sut 无 jsonl_root
    assert sut.replay_status() == "not_started"
    rr = sut.replay_from_jsonl(project_id=mock_project_id)
    assert rr.replayed_count == 0
    assert rr.latest_hash == "0" * 64
    assert rr.hash_chain_valid is True
    assert sut.replay_status() == "no_root"


# ---------------------------------------------------------------------------
# TC-E07 · replay 空 audit_dir · status=no_data
# ---------------------------------------------------------------------------


def test_TC_L101_L205_E07_replay_empty_audit_dir_sets_status_no_data(
    make_recorder, mock_project_id, tmp_path
) -> None:
    rec = make_recorder(session_active_pid=mock_project_id, jsonl_root=tmp_path)
    rr = rec.replay_from_jsonl(project_id=mock_project_id)
    assert rr.replayed_count == 0
    assert rr.latest_hash == "0" * 64
    assert rec.replay_status() == "no_data"
