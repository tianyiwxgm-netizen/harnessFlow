"""IC-01 · 7 态全转换 · 12 合法边 + 非法边 拒绝.

7 态:
    NOT_EXIST · INITIALIZED · PLANNING · TDD_PLANNING · EXECUTING · CLOSING · CLOSED

12 合法边(对齐 L1-02 stage_gate.schemas.ALLOWED_TRANSITIONS):
    1. NOT_EXIST → INITIALIZED
    2. INITIALIZED → PLANNING
    3. PLANNING → TDD_PLANNING
    4. TDD_PLANNING → EXECUTING
    5. EXECUTING → CLOSING
    6. CLOSING → CLOSED
    7. PLANNING → PLANNING (Re-open 自环)
    8. TDD_PLANNING → TDD_PLANNING (Re-open 自环)
    9. EXECUTING → TDD_PLANNING (L1-04 回退)
    10. EXECUTING → PLANNING (L1-04 回退)
    11. PLANNING → CLOSED (紧急终止)
    12. TDD_PLANNING → CLOSED (紧急终止)

覆盖:
    - 12 正向 · 每条合法边 1 TC(此文件)
    - 7 态 · `get_current_state()` 返回正确 state
    - 非法边示例若干(NOT_EXIST→CLOSED / PLANNING→EXECUTING / CLOSED→任何)
"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine.schemas import E_TRANS_INVALID_NEXT


# ==============================================================================
# 12 合法边 × 每条 1 TC
# ==============================================================================


LEGAL_EDGES = [
    ("NOT_EXIST", "INITIALIZED"),
    ("INITIALIZED", "PLANNING"),
    ("PLANNING", "TDD_PLANNING"),
    ("TDD_PLANNING", "EXECUTING"),
    ("EXECUTING", "CLOSING"),
    ("CLOSING", "CLOSED"),
    ("PLANNING", "PLANNING"),       # Re-open 自环
    ("TDD_PLANNING", "TDD_PLANNING"),  # Re-open 自环
    ("EXECUTING", "TDD_PLANNING"),   # L1-04 回退
    ("EXECUTING", "PLANNING"),       # L1-04 回退
    ("PLANNING", "CLOSED"),          # 紧急终止
    ("TDD_PLANNING", "CLOSED"),      # 紧急终止
]


@pytest.mark.parametrize("frm,to", LEGAL_EDGES, ids=[f"{f}->{t}" for f, t in LEGAL_EDGES])
def test_legal_edge_accepted(
    build_at_state, make_request, project_id: str, frm: str, to: str,
) -> None:
    """12 合法边全部放行 · accepted=True · new_state==to."""
    orch = build_at_state(project_id, frm)
    req = make_request(from_state=frm, to_state=to)
    result = orch.transition(req)
    assert result.accepted is True, f"{frm} → {to} 应合法 · 实际被拒"
    assert result.new_state == to
    assert result.error_code is None
    assert orch.get_current_state() == to


# ==============================================================================
# 非法边 × 若干
# ==============================================================================


ILLEGAL_EDGES = [
    # 跳过 INITIALIZED 直接 planning
    ("NOT_EXIST", "PLANNING"),
    # 跳过 TDD_PLANNING
    ("PLANNING", "EXECUTING"),
    # 终态出边 · CLOSED 无出边
    ("CLOSED", "INITIALIZED"),
    ("CLOSED", "PLANNING"),
    # CLOSING 不能回退
    ("CLOSING", "PLANNING"),
]


@pytest.mark.parametrize(
    "frm,to", ILLEGAL_EDGES, ids=[f"{f}-x-{t}" for f, t in ILLEGAL_EDGES],
)
def test_illegal_edge_rejected_with_error_code(
    build_at_state, make_request, project_id: str, frm: str, to: str,
) -> None:
    """非法边 · accepted=False · error_code=E_TRANS_INVALID_NEXT · state 不变."""
    orch = build_at_state(project_id, frm)
    req = make_request(from_state=frm, to_state=to)
    result = orch.transition(req)
    assert result.accepted is False
    assert result.error_code == E_TRANS_INVALID_NEXT
    assert orch.get_current_state() == frm  # 状态不变


# ==============================================================================
# allowed_next 查询 · 7 态每态都可查
# ==============================================================================


class TestAllowedNextQuery:
    """§3.2 allowed_next · 纯函数 · O(1) · 7 态都能查."""

    def test_not_exist_allows_only_initialized(
        self, build_at_state, project_id: str,
    ) -> None:
        orch = build_at_state(project_id, "NOT_EXIST")
        assert orch.allowed_next("NOT_EXIST") == ("INITIALIZED",)

    def test_planning_allows_4_options(
        self, build_at_state, project_id: str,
    ) -> None:
        orch = build_at_state(project_id, "PLANNING")
        # {PLANNING, TDD_PLANNING, CLOSED} 3 个(sorted)
        nexts = orch.allowed_next("PLANNING")
        assert set(nexts) == {"PLANNING", "TDD_PLANNING", "CLOSED"}

    def test_closed_is_terminal_no_outgoing(
        self, build_at_state, project_id: str,
    ) -> None:
        orch = build_at_state(project_id, "CLOSED")
        assert orch.allowed_next("CLOSED") == ()
