"""L2-03 · §1 transition_table · 12 合法边 + allowed_next + is_allowed (TC-14..17)。"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine import (
    ALLOWED_TRANSITIONS,
    E_TRANS_INVALID_STATE_ENUM,
    STATES,
    StateMachineError,
    allowed_next,
    is_allowed,
)
from app.main_loop.state_machine.transition_table import count_edges


EXPECTED_12_EDGES = {
    ("NOT_EXIST", "INITIALIZED"),
    ("INITIALIZED", "PLANNING"),
    ("PLANNING", "TDD_PLANNING"),
    ("TDD_PLANNING", "EXECUTING"),
    ("EXECUTING", "CLOSING"),
    ("CLOSING", "CLOSED"),
    ("PLANNING", "PLANNING"),
    ("TDD_PLANNING", "TDD_PLANNING"),
    ("EXECUTING", "TDD_PLANNING"),
    ("EXECUTING", "PLANNING"),
    ("PLANNING", "CLOSED"),
    ("TDD_PLANNING", "CLOSED"),
}


class TestTransitionTable:
    def test_tc14_count_12_edges(self):
        """TC-14 · ALLOWED_TRANSITIONS 必须 12 条 (运行时 assert 兜底)。"""
        assert count_edges() == 12
        assert len(ALLOWED_TRANSITIONS) == 12

    def test_tc15_all_12_edges_match_spec(self):
        """TC-15 · 12 条边内容与 §3 列表逐字对齐。"""
        actual = {t.as_tuple() for t in ALLOWED_TRANSITIONS}
        assert actual == EXPECTED_12_EDGES

    def test_tc16_is_allowed_all_12_yes(self):
        """TC-16 · is_allowed(from,to)=True 对全部 12 合法对。"""
        for frm, to in EXPECTED_12_EDGES:
            assert is_allowed(frm, to), f"{frm}->{to} should be allowed"

    def test_tc17_is_allowed_illegal_skip(self):
        """TC-17 · 非法跳跃 (NOT_EXIST→PLANNING / INITIALIZED→EXECUTING) False。"""
        illegal = [
            ("NOT_EXIST", "PLANNING"),
            ("NOT_EXIST", "EXECUTING"),
            ("NOT_EXIST", "CLOSED"),
            ("INITIALIZED", "EXECUTING"),
            ("INITIALIZED", "CLOSING"),
            ("INITIALIZED", "CLOSED"),
            ("PLANNING", "EXECUTING"),  # 必须先过 TDD_PLANNING
            ("PLANNING", "CLOSING"),
            ("TDD_PLANNING", "CLOSING"),
            ("EXECUTING", "CLOSED"),
            ("CLOSING", "PLANNING"),  # 收尾后无返
            ("CLOSED", "INITIALIZED"),  # 终态无出
        ]
        for frm, to in illegal:
            assert not is_allowed(frm, to), f"{frm}->{to} must be rejected"


class TestAllowedNext:
    def test_tc18_allowed_next_terminal_empty(self):
        """TC-18 · CLOSED 终态 allowed_next 空 tuple。"""
        assert allowed_next("CLOSED") == ()

    def test_tc19_allowed_next_sorted_stable(self):
        """TC-19 · allowed_next 返回 sorted tuple (稳定序,便于测试断言)。"""
        # PLANNING 出度: PLANNING, TDD_PLANNING, CLOSED (共 3)
        got = allowed_next("PLANNING")
        assert isinstance(got, tuple)
        assert got == tuple(sorted(got))
        assert set(got) == {"PLANNING", "TDD_PLANNING", "CLOSED"}

    def test_tc20_allowed_next_invalid_enum_raises(self):
        """TC-20 · 非 7-enum 抛 E_TRANS_INVALID_STATE_ENUM。"""
        with pytest.raises(StateMachineError) as exc:
            allowed_next("S1")  # 9-态残留
        assert exc.value.error_code == E_TRANS_INVALID_STATE_ENUM

    def test_tc21_allowed_next_executing_three_outs(self):
        """TC-21 · EXECUTING 有 3 出边: CLOSING / TDD_PLANNING / PLANNING。"""
        got = set(allowed_next("EXECUTING"))
        assert got == {"CLOSING", "TDD_PLANNING", "PLANNING"}

    def test_tc22_each_of_7_states_has_entry(self):
        """TC-22 · STATES 7 态都有 allowed_next entry (即使是空)。"""
        for st in STATES:
            # 不应 raise
            _ = allowed_next(st)
