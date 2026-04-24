"""L2-03 · §2 正向用例 · 自环 & L1-04 回退 & 紧急终止 (TC-08 ~ TC-12)。"""
from __future__ import annotations


def _drive(orch, make_request, path):
    last = None
    for frm, to in path:
        req = make_request(from_state=frm, to_state=to)
        last = orch.transition(req)
        assert last.accepted is True, f"{frm}->{to} rejected unexpectedly"
    return last


class TestSelfLoopAndRollback:
    def test_tc08_planning_reopen_selfloop(self, orchestrator, make_request):
        """TC-08 · PLANNING → PLANNING · Re-open 自环(合法边 #7)。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
            ],
        )
        req = make_request(from_state="PLANNING", to_state="PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "PLANNING"
        assert orchestrator.get_current_state() == "PLANNING"
        # version 仍累加
        assert orchestrator.snapshot.version == 3

    def test_tc09_tdd_planning_reopen_selfloop(self, orchestrator, make_request):
        """TC-09 · TDD_PLANNING → TDD_PLANNING · 自环(合法边 #8)。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
                ("PLANNING", "TDD_PLANNING"),
            ],
        )
        req = make_request(from_state="TDD_PLANNING", to_state="TDD_PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"

    def test_tc10_executing_rollback_to_tdd_planning(
        self, orchestrator, make_request
    ):
        """TC-10 · EXECUTING → TDD_PLANNING · L1-04 回退(合法边 #9)。"""
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
        req = make_request(
            from_state="EXECUTING",
            to_state="TDD_PLANNING",
            reason="rollback to tdd_planning L1-04 verifier heavy fail",
        )
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "TDD_PLANNING"
        assert orchestrator.get_current_state() == "TDD_PLANNING"

    def test_tc11_executing_rollback_to_planning(
        self, orchestrator, make_request
    ):
        """TC-11 · EXECUTING → PLANNING · L1-04 深度回退(合法边 #10)。"""
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
        req = make_request(
            from_state="EXECUTING",
            to_state="PLANNING",
            reason="rollback to planning L1-04 scope redesign required",
        )
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "PLANNING"

    def test_tc12_planning_emergency_close(self, orchestrator, make_request):
        """TC-12 · PLANNING → CLOSED · 紧急终止(合法边 #11)。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
            ],
        )
        req = make_request(
            from_state="PLANNING",
            to_state="CLOSED",
            reason="emergency termination by user kill signal received",
        )
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "CLOSED"

    def test_tc13_tdd_planning_emergency_close(self, orchestrator, make_request):
        """TC-13 · TDD_PLANNING → CLOSED · 紧急终止(合法边 #12)。"""
        _drive(
            orchestrator,
            make_request,
            [
                ("NOT_EXIST", "INITIALIZED"),
                ("INITIALIZED", "PLANNING"),
                ("PLANNING", "TDD_PLANNING"),
            ],
        )
        req = make_request(
            from_state="TDD_PLANNING",
            to_state="CLOSED",
            reason="emergency termination from tdd_planning context signal kill",
        )
        result = orchestrator.transition(req)
        assert result.accepted is True
        assert result.new_state == "CLOSED"
