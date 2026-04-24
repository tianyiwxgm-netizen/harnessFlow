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
