"""L2-03 · §2 正向用例 · 核心转换路径 (TC-01 ~ TC-07)。"""
from __future__ import annotations


def _drive(orch, make_request, path):
    """按 path 顺序驱动 orchestrator 走多步转换,返回最后 result。"""
    last = None
    for frm, to in path:
        req = make_request(from_state=frm, to_state=to)
        last = orch.transition(req)
        assert last.accepted is True, f"{frm}->{to} should accept"
    return last


class TestHappyPath:
    def test_tc01_not_exist_to_initialized(self, orchestrator, make_request):
        """TC-01 · NOT_EXIST → INITIALIZED · 最基础转换 · accepted=True。"""
        req = make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "INITIALIZED"
        assert result.transition_id == req.transition_id
        assert result.error_code is None
        assert result.reason is None
        assert orchestrator.get_current_state() == "INITIALIZED"
        assert orchestrator.snapshot.version == 1

    def test_tc02_initialized_to_planning(self, orchestrator, make_request):
        """TC-02 · INITIALIZED → PLANNING · 第二步。"""
        _drive(orchestrator, make_request, [("NOT_EXIST", "INITIALIZED")])
        req = make_request(from_state="INITIALIZED", to_state="PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "PLANNING"
        assert orchestrator.get_current_state() == "PLANNING"
        assert orchestrator.snapshot.version == 2

    def test_tc03_planning_to_tdd_planning(self, orchestrator, make_request):
        """TC-03 · PLANNING → TDD_PLANNING · §3 规划→TDD。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
            ],
        )
        req = make_request(from_state="PLANNING", to_state="TDD_PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"

    def test_tc04_tdd_planning_to_executing(self, orchestrator, make_request):
        """TC-04 · TDD_PLANNING → EXECUTING · 开工。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
                ("PLANNING", "TDD_PLANNING"),
            ],
        )
        req = make_request(from_state="TDD_PLANNING", to_state="EXECUTING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "EXECUTING"

    def test_tc05_executing_to_closing(self, orchestrator, make_request):
        """TC-05 · EXECUTING → CLOSING · 完工入收尾。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
                ("PLANNING", "TDD_PLANNING"),
                ("TDD_PLANNING", "EXECUTING"),
            ],
        )
        req = make_request(from_state="EXECUTING", to_state="CLOSING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "CLOSING"

    def test_tc06_closing_to_closed(self, orchestrator, make_request):
        """TC-06 · CLOSING → CLOSED · 终态。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
                ("PLANNING", "TDD_PLANNING"),
                ("TDD_PLANNING", "EXECUTING"),
                ("EXECUTING", "CLOSING"),
            ],
        )
        req = make_request(from_state="CLOSING", to_state="CLOSED")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "CLOSED"
        assert orchestrator.get_current_state() == "CLOSED"

    def test_tc07_full_main_chain_6_edges(self, orchestrator, make_request):
        """TC-07 · 完整主链 NOT_EXIST→...→CLOSED · 6 条边 · version 累加 6。"""
        path = [
            ("NOT_EXIST", "INITIALIZED"),
            ("INITIALIZED", "PLANNING"),
            ("PLANNING", "TDD_PLANNING"),
            ("TDD_PLANNING", "EXECUTING"),
            ("EXECUTING", "CLOSING"),
            ("CLOSING", "CLOSED"),
        ]
        last = _drive(orchestrator, make_request, path)
        assert last.new_state == "CLOSED"
        assert orchestrator.snapshot.version == 6
        assert len(orchestrator.snapshot.history) == 6
        # 所有 history 条目 accepted=True
        assert all(r.accepted for r in orchestrator.snapshot.history)
