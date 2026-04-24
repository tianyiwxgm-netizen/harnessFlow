"""IC-04 · 5 负向 TC · invoke_skill 错误路径.

覆盖:
    TC-1 · 缺 project_id (空字符串) → ValidationError
    TC-2 · project_id 跨 (context pid != top pid) → PM-14 拒绝
    TC-3 · capability 不存在 → success=False + E_SKILL_NO_CAPABILITY
    TC-4 · 超时 → SkillTimeout 触发 fallback (或全链失败)
    TC-5 · LLM/skill 连续 raise (模拟 LLM 故障) → success=False + E_SKILL_ALL_FALLBACK_FAIL
"""
from __future__ import annotations

import time

import pytest

from app.skill_dispatch.invoker.schemas import InvocationRequest


class TestIC04Negative:
    """5 负向 · 字段违规 / 跨 pid / capability 未注册 / 超时 / LLM fail."""

    # ---- TC-1 · 缺 project_id ----
    def test_missing_project_id_rejected_at_schema(self, project_id: str) -> None:
        """空 project_id · Pydantic min_length 拒绝 · 不到达 Executor."""
        with pytest.raises(ValueError):
            InvocationRequest(
                invocation_id="inv-neg-1",
                project_id="",   # 空
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": ""},
            )

    # ---- TC-2 · context pid 跨 ----
    def test_context_project_id_mismatch_rejected(self, project_id: str) -> None:
        """PM-14 根字段守恒 · top pid ≠ context pid · ValidationError."""
        with pytest.raises(ValueError, match="project_id.*mismatch"):
            InvocationRequest(
                invocation_id="inv-neg-2",
                project_id=project_id,
                capability="write_test",
                params={},
                caller_l1="L1-04",
                context={"project_id": "other_pid"},
            )

    # ---- TC-3 · capability 不存在 ----
    def test_unknown_capability_returns_no_capability(
        self, make_executor, project_id: str,
    ) -> None:
        def runner(skill, params, ctx):
            return {"unreached": True}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-neg-3",
            project_id=project_id,
            capability="this_capability_does_not_exist",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is False
        assert rsp.error["code"] == "E_SKILL_NO_CAPABILITY"

    # ---- TC-4 · 超时 ----
    def test_skill_timeout_triggers_fallback(
        self, make_executor, project_id: str,
    ) -> None:
        """primary 超时 · fallback 命中 · 总体 success=True."""

        def runner(skill, params, ctx):
            if skill.skill_id == "superpowers:tdd-workflow":
                # primary 慢 · 主动 sleep 触发 timeout_ms
                time.sleep(0.3)
                return {"ok": False}
            return {"ok_via_fallback": True}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-neg-4",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
            timeout_ms=100,   # primary 会超时
        )
        rsp = exe.invoke(req)
        # 实际业务不可能在 100ms 内完成 · fallback 承接
        assert rsp.success is True
        assert rsp.fallback_used is True
        assert rsp.skill_id == "builtin:write_test_min"
        assert rsp.result == {"ok_via_fallback": True}

    # ---- TC-5 · LLM 连续 fail → 全链失败 ----
    def test_all_candidates_fail_returns_success_false(
        self, make_executor, project_id: str,
    ) -> None:
        """模拟 LLM 全链故障 · 契约红线: 必须 success=False + error · 不能 raise."""

        def runner(skill, params, ctx):
            raise ConnectionError(f"LLM 503 for {skill.skill_id}")

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-neg-5",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is False
        assert rsp.error["code"] == "E_SKILL_ALL_FALLBACK_FAIL"
        assert len(rsp.fallback_trace) == 2
        # 两个候选都试过
        skill_ids_in_trace = [t["skill_id"] for t in rsp.fallback_trace]
        assert "superpowers:tdd-workflow" in skill_ids_in_trace
        assert "builtin:write_test_min" in skill_ids_in_trace
