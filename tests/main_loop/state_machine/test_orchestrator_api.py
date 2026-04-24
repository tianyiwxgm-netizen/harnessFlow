"""L2-03 · orchestrator public API · snapshot / allowed_next / audit_id (TC-49..52)。"""
from __future__ import annotations

import pytest

from app.main_loop.state_machine import (
    E_TRANS_NO_PROJECT_ID,
    StateMachineError,
    StateMachineOrchestrator,
    TransitionResult,
)


class TestOrchestratorCtor:
    def test_tc49_ctor_requires_project_id(self, clock_iter):
        """TC-49 · 构造时 project_id='' → E_TRANS_NO_PROJECT_ID。"""
        with pytest.raises(StateMachineError) as exc:
            StateMachineOrchestrator(project_id="", clock=clock_iter)
        assert exc.value.error_code == E_TRANS_NO_PROJECT_ID

    def test_tc50_ctor_default_snapshot_state(self, project_id, clock_iter):
        """TC-50 · 默认 initial_state=NOT_EXIST · version=0 · history 空。"""
        orch = StateMachineOrchestrator(project_id=project_id, clock=clock_iter)
        assert orch.get_current_state() == "NOT_EXIST"
        assert orch.snapshot.version == 0
        assert orch.snapshot.history == []
        assert orch.project_id == project_id


class TestOrchestratorAllowedNext:
    def test_tc51_orchestrator_allowed_next_delegates(self, orchestrator):
        """TC-51 · orchestrator.allowed_next(PLANNING) 与 module 级一致。"""
        got = orchestrator.allowed_next("PLANNING")
        assert set(got) == {"PLANNING", "TDD_PLANNING", "CLOSED"}


class TestAuditEntryIdPropagation:
    def test_tc52_audit_entry_id_transferred_on_success(
        self, project_id, clock_iter, make_request
    ):
        """TC-52 · audit_sink 返回 id · result.audit_entry_id 等于它。"""
        def good_audit(res: TransitionResult) -> str:
            return "audit-abc-123"

        orch = StateMachineOrchestrator(
            project_id=project_id, clock=clock_iter, audit_sink=good_audit
        )
        req = make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        result = orch.transition(req)
        assert result.accepted is True
        assert result.audit_entry_id == "audit-abc-123"
        # history 里的那条也是带 audit_entry_id 的 (同引用)
        assert orch.snapshot.history[-1].audit_entry_id == "audit-abc-123"

    def test_tc53_history_records_both_accepted_and_rejected(
        self, orchestrator, make_request
    ):
        """TC-53 · history 同时收录成功和拒绝事件 (便于审计/回放)。"""
        # 1 次 accept
        r1 = orchestrator.transition(
            make_request(from_state="NOT_EXIST", to_state="INITIALIZED")
        )
        assert r1.accepted is True
        # 1 次 reject (INVALID_NEXT)
        r2 = orchestrator.transition(
            make_request(from_state="INITIALIZED", to_state="EXECUTING")
        )
        assert r2.accepted is False
        assert len(orchestrator.snapshot.history) == 2
        assert orchestrator.snapshot.history[0].accepted is True
        assert orchestrator.snapshot.history[1].accepted is False
