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
