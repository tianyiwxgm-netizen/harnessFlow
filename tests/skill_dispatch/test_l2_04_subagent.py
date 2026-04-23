"""L2-04 子 Agent 委托器 · IC-05/12/20 · 共 ~40 TC.

文档参照:
  - docs/3-1-Solution-Technical/L1-05-Skill生态+子Agent调度/L2-04-子 Agent 委托器.md
  - docs/3-1-Solution-Technical/integration/ic-contracts.md §3.5/3.12/3.20
  - docs/superpowers/plans/Dev-γ-impl.md §6

错误码:
  E_SUB_NO_PROJECT_ID / ROLE_UNKNOWN / BRIEF_TOO_SHORT / SESSION_LIMIT /
  TIMEOUT / TOOL_ERROR / CONTEXT_ISOLATION_VIOLATION / TOOL_NOT_ALLOWED /
  SPAWN_FAILED / RESOURCE_QUOTA_EXCEEDED
  E_OB_REPO_PATH_INVALID / REPO_TOO_LARGE / TIMEOUT / KB_WRITE_FAIL
  E_VER_MUST_BE_INDEPENDENT_SESSION / TIMEOUT / EVIDENCE_INCOMPLETE / TOOL_DENIED
"""
from __future__ import annotations

import pytest


class TestSubagentSchemas:
    """Task 04.1 · Pydantic 3 IC 请求/响应 + LifecycleState 状态机."""

    def test_ic05_request_required_fields(self):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        req = DelegationRequest(
            delegation_id="del1",
            project_id="p1",
            role="researcher",
            task_brief="Research best open-source LLM evaluation frameworks (≥ 50 chars)",
            context_copy={"project_id": "p1", "wp_id": "wp1"},
            caller_l1="L1-04",
        )
        assert req.timeout_s == 1800   # default

    def test_ic05_rejects_brief_too_short(self):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        with pytest.raises(ValueError, match="task_brief"):
            DelegationRequest(
                delegation_id="d",
                project_id="p1",
                role="researcher",
                task_brief="too short",   # < 50
                context_copy={"project_id": "p1"},
                caller_l1="L1-04",
            )

    def test_ic05_rejects_unknown_role(self):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        with pytest.raises(ValueError):
            DelegationRequest(
                delegation_id="d",
                project_id="p1",
                role="hacker",   # type: ignore[arg-type]
                task_brief="A" * 60,
                context_copy={"project_id": "p1"},
                caller_l1="L1-04",
            )

    def test_ic05_context_copy_pm14_mirror(self):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        with pytest.raises(ValueError, match="project_id.*mismatch"):
            DelegationRequest(
                delegation_id="d",
                project_id="p1",
                role="researcher",
                task_brief="A" * 60,
                context_copy={"project_id": "p2"},
                caller_l1="L1-04",
            )

    def test_ic12_codebase_onboarding_request(self):
        from app.skill_dispatch.subagent.schemas import CodebaseOnboardingRequest

        req = CodebaseOnboardingRequest(
            delegation_id="d",
            project_id="p1",
            repo_path="/tmp/repo",
            kb_write_back=True,
        )
        assert req.timeout_s == 600

    def test_ic20_verifier_request_strict_tool_whitelist(self):
        from app.skill_dispatch.subagent.schemas import VerifierRequest

        req = VerifierRequest(
            delegation_id="d",
            project_id="p1",
            wp_id="wp1",
            blueprint_slice={"req": "do X"},
            s4_snapshot={"diff": "..."},
            acceptance_criteria=["A", "B"],
        )
        # 默认 tool_whitelist 严格限制
        assert set(req.allowed_tools) == {"Read", "Glob", "Grep", "Bash"}

    def test_ic20_rejects_extra_tool_in_whitelist(self):
        from app.skill_dispatch.subagent.schemas import VerifierRequest

        with pytest.raises(ValueError, match="allowed_tools"):
            VerifierRequest(
                delegation_id="d",
                project_id="p1",
                wp_id="wp1",
                blueprint_slice={},
                s4_snapshot={},
                acceptance_criteria=[],
                allowed_tools=["Read", "Bash", "Write"],  # Write 禁用
            )

    def test_dispatch_ack_minimal(self):
        from app.skill_dispatch.subagent.schemas import DispatchAck

        ack = DispatchAck(delegation_id="d", dispatched=True, subagent_session_id="s1")
        assert ack.dispatched is True

    def test_final_report_status_enum(self):
        from app.skill_dispatch.subagent.schemas import FinalReport

        r = FinalReport(
            delegation_id="d",
            subagent_session_id="s1",
            status="success",
            artifacts=[{"path": "x"}],
        )
        assert r.status == "success"

    def test_final_report_rejects_invalid_status(self):
        from app.skill_dispatch.subagent.schemas import FinalReport

        with pytest.raises(ValueError):
            FinalReport(
                delegation_id="d",
                subagent_session_id="s1",
                status="exploded",   # type: ignore[arg-type]
                artifacts=[],
            )

    def test_lifecycle_state_enum(self):
        from app.skill_dispatch.subagent.schemas import LifecycleState

        assert LifecycleState.PROVISIONING.value == "provisioning"
        assert LifecycleState.RUNNING.value == "running"
        assert LifecycleState.COMPLETED.value == "completed"
        assert LifecycleState.KILLED.value == "killed"

    def test_verifier_verdict_enum(self):
        from app.skill_dispatch.subagent.schemas import VerdictOutcome

        vals = {v.value for v in VerdictOutcome}
        assert vals == {"PASS", "FAIL_L1", "FAIL_L2", "FAIL_L3", "FAIL_L4"}
