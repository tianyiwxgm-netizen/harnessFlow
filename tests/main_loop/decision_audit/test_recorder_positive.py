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
