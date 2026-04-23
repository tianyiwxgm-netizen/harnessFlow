"""PM-14 物理分片 + PM-03 独立 session 的 e2e 隔离验证.

文档参照:
  - docs/superpowers/plans/Dev-γ-impl.md §8 Task 06.3
  - docs/3-1-Solution-Technical/projectModel/tech-design.md §9 (PM-14)
"""
from __future__ import annotations

import pytest


@pytest.mark.pm14
@pytest.mark.pm03
class TestSubagentIsolation:
    """组内 PM-14 + PM-03 隔离铁律."""

    def test_pm14_child_inherits_parent_project_id(self):
        from app.skill_dispatch.subagent.context_scope import make_child_context

        parent = {"project_id": "p1", "wp_id": "wp1"}
        child, _ = make_child_context(parent, child_project_id="p1")
        assert child["project_id"] == "p1"

    def test_pm14_cross_project_delegate_rejected(self):
        """父 ctx.pid = p1 · 申请 child_pid = p_other → 立即 raise."""
        from app.skill_dispatch.subagent.context_scope import (
            ContextIsolationViolation,
            make_child_context,
        )

        with pytest.raises(ContextIsolationViolation):
            make_child_context(
                {"project_id": "p1"},
                child_project_id="p_other",
            )

    def test_pm03_child_cannot_read_main_task_board(self):
        """主 session 把 task_board 塞 ctx · 子 Agent 只读 ctx 不包含 task_board."""
        from app.skill_dispatch.subagent.context_scope import make_child_context

        parent = {
            "project_id": "p1",
            "wp_id": "wp1",
            "task_board": {"main_session_state": "SECRET"},
            "internal_secret": "do-not-leak",
        }
        child, _ = make_child_context(parent, child_project_id="p1")
        assert "task_board" not in child
        assert "internal_secret" not in child

    def test_pm03_child_context_is_read_only(self):
        """MappingProxyType 保证子 Agent 无法反向写回父 session."""
        from app.skill_dispatch.subagent.context_scope import make_child_context

        child, _ = make_child_context({"project_id": "p1"}, child_project_id="p1")
        with pytest.raises(TypeError):
            child["injected"] = "attempt"   # type: ignore[index]

    def test_pm14_all_ic_writes_require_project_id(self):
        """IC-04/05/12/20 入参 schema 必 reject 空 project_id."""
        from app.skill_dispatch.invoker.schemas import InvocationRequest
        from app.skill_dispatch.subagent.schemas import (
            CodebaseOnboardingRequest,
            DelegationRequest,
            VerifierRequest,
        )

        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="i", project_id="", capability="c",
                params={}, caller_l1="L1-04", context={"project_id": ""},
            )
        with pytest.raises(ValueError):
            DelegationRequest(
                delegation_id="d", project_id="", role="researcher",
                task_brief="A" * 60, context_copy={"project_id": ""}, caller_l1="L1-04",
            )
        with pytest.raises(ValueError):
            CodebaseOnboardingRequest(
                delegation_id="d", project_id="", repo_path="/tmp", kb_write_back=True,
            )
        with pytest.raises(ValueError):
            VerifierRequest(
                delegation_id="d", project_id="", wp_id="wp1",
                blueprint_slice={}, s4_snapshot={}, acceptance_criteria=[],
            )
