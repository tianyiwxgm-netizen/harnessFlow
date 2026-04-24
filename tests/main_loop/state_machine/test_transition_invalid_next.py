"""L2-03 · §3 负向 · E_TRANS_INVALID_NEXT / E_TRANS_STATE_MISMATCH (TC-23..26)。"""
from __future__ import annotations

from app.main_loop.state_machine import E_TRANS_INVALID_NEXT, E_TRANS_STATE_MISMATCH


class TestInvalidNext:
    def test_tc23_not_exist_to_planning_rejected(self, orchestrator, make_request):
        """TC-23 · NOT_EXIST→PLANNING 不在 allowed_next 表 · accepted=False。"""
        req = make_request(from_state="NOT_EXIST", to_state="PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is False
        assert result.error_code == E_TRANS_INVALID_NEXT
        assert "not in allowed_next" in (result.reason or "")
        # snapshot 不变
        assert orchestrator.get_current_state() == "NOT_EXIST"
        assert orchestrator.snapshot.version == 0

    def test_tc24_initialized_to_executing_skip_rejected(
        self, orchestrator, make_request
    ):
        """TC-24 · INITIALIZED→EXECUTING 跳 2 级 · accepted=False。"""
        # 驱到 INITIALIZED
        r0 = orchestrator.transition(
            make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        )
        assert r0.accepted is True
        # 非法跳跃
        req = make_request(from_state="INITIALIZED", to_state="EXECUTING")
        result = orchestrator.transition(req)
        assert result.accepted is False
        assert result.error_code == E_TRANS_INVALID_NEXT
        assert orchestrator.get_current_state() == "INITIALIZED"
        # version 不累加
        assert orchestrator.snapshot.version == 1

    def test_tc25_closed_no_outgoing(self, orchestrator, make_request):
        """TC-25 · CLOSED 终态无出边 · CLOSED→INITIALIZED 被拒。"""
        # 走完整主链到 CLOSED
        path = [
            ("NOT_EXIST", "INITIALIZED"),
            ("INITIALIZED", "PLANNING"),
            ("PLANNING", "TDD_PLANNING"),
            ("TDD_PLANNING", "EXECUTING"),
            ("EXECUTING", "CLOSING"),
            ("CLOSING", "CLOSED"),
        ]
        for frm, to in path:
            orchestrator.transition(make_request(from_state=frm, to_state=to))
        assert orchestrator.get_current_state() == "CLOSED"

        # 试图从 CLOSED 出去
        req = make_request(from_state="CLOSED", to_state="INITIALIZED")
        result = orchestrator.transition(req)
        assert result.accepted is False
        assert result.error_code == E_TRANS_INVALID_NEXT


class TestStateMismatch:
    def test_tc26_req_from_mismatch_snapshot(self, orchestrator, make_request):
        """TC-26 · req.from=PLANNING 但 snapshot=NOT_EXIST · E_TRANS_STATE_MISMATCH。"""
        req = make_request(from_state="PLANNING", to_state="TDD_PLANNING")
        result = orchestrator.transition(req)
        assert result.accepted is False
        assert result.error_code == E_TRANS_STATE_MISMATCH
        assert "state mismatch" in (result.reason or "")
        assert orchestrator.get_current_state() == "NOT_EXIST"
