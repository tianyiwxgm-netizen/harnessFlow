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
