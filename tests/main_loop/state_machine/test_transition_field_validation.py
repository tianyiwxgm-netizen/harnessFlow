"""L2-03 · §3 负向 · 字段级硬约束 (TC-27..33) · 全部 raise StateMachineError。"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine import (
    E_TRANS_CROSS_PROJECT,
    E_TRANS_INVALID_STATE_ENUM,
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    E_TRANS_TRANSITION_ID_FORMAT,
    StateMachineError,
)


class TestFieldValidation:
    def test_tc27_no_project_id_raises(self, orchestrator, make_request):
        """TC-27 · req.project_id='' → E_TRANS_NO_PROJECT_ID。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            project_id_override="",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID

    def test_tc28_project_id_bad_format_raises(self, orchestrator, make_request):
        """TC-28 · project_id 不匹配 `pid-{uuid}` → E_TRANS_NO_PROJECT_ID。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            project_id_override="random-string-not-pid",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID

    def test_tc29_cross_project_raises(self, orchestrator, make_request):
        """TC-29 · req.project_id ≠ 绑定 pid → E_TRANS_CROSS_PROJECT。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            project_id_override="pid-99999999-9999-9999-9999-999999999999",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_CROSS_PROJECT

    def test_tc30_reason_too_short_raises(self, orchestrator, make_request):
        """TC-30 · reason 长度 < 20 → E_TRANS_REASON_TOO_SHORT。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            reason="short",  # 5 字
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_REASON_TOO_SHORT

    def test_tc31_no_evidence_raises(self, orchestrator, make_request):
        """TC-31 · evidence_refs 空 tuple → E_TRANS_NO_EVIDENCE。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            evidence_refs=(),
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_NO_EVIDENCE

    def test_tc32_invalid_state_enum_from_raises(
        self, orchestrator, make_request
    ):
        """TC-32 · req.from_state 非 7-enum (S1 旧名) → INVALID_STATE_ENUM。"""
        req = make_request(from_state="S1", to_state="INITIALIZED")  # type: ignore[arg-type]
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_INVALID_STATE_ENUM

    def test_tc33_invalid_state_enum_to_raises(self, orchestrator, make_request):
        """TC-33 · req.to_state 非 7-enum → INVALID_STATE_ENUM。"""
        req = make_request(from_state="NOT_EXIST", to_state="HALTED")  # type: ignore[arg-type]
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_INVALID_STATE_ENUM

    def test_tc34_transition_id_bad_format_raises(
        self, orchestrator, make_request
    ):
        """TC-34 · transition_id 不匹配 `trans-{uuid}` → TRANSITION_ID_FORMAT。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id="bad-format-123",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_TRANSITION_ID_FORMAT

    def test_tc35_transition_id_empty_raises(self, orchestrator, make_request):
        """TC-35 · transition_id='' → TRANSITION_ID_FORMAT。"""
        req = make_request(
            from_state="NOT_EXIST",
            to_state="INITIALIZED",
            transition_id="",
        )
        with pytest.raises(StateMachineError) as exc:
            orchestrator.transition(req)
        assert exc.value.error_code == E_TRANS_TRANSITION_ID_FORMAT
