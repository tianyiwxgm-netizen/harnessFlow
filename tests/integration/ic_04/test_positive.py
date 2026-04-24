"""IC-04 · 5 正向 TC · invoke_skill happy path.

覆盖:
    TC-1 · primary skill 成功 · success=True
    TC-2 · primary 失败 → fallback 命中 · fallback_used=True
    TC-3 · 白名单 context 传递 (ContextInjector 过滤)
    TC-4 · params 透传 + 结果回包
    TC-5 · IC-09 skill_invocation_started + finished 审计
"""
from __future__ import annotations

from app.skill_dispatch.invoker.schemas import InvocationRequest


class TestIC04Positive:
    """5 正向 · primary / fallback / context / params / audit."""

    # ---- TC-1 · primary 成功 ----
    def test_primary_skill_success(self, make_executor, project_id: str) -> None:
        def runner(skill, params, ctx):
            return {"ok": True, "echoed": params.get("x")}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-pos-1",
            project_id=project_id,
            capability="write_test",
            params={"x": 42},
            caller_l1="L1-04",
            context={"project_id": project_id, "wp_id": "wp-1"},
        )
        rsp = exe.invoke(req)
        assert rsp.success is True
        assert rsp.result == {"ok": True, "echoed": 42}
        assert rsp.fallback_used is False
        assert rsp.skill_id == "superpowers:tdd-workflow"

    # ---- TC-2 · primary 失败 → fallback ----
    def test_primary_fail_falls_back(self, make_executor, project_id: str) -> None:
        called: list[str] = []

        def runner(skill, params, ctx):
            called.append(skill.skill_id)
            if skill.skill_id == "superpowers:tdd-workflow":
                raise ValueError("primary dead")
            return {"ok_from": skill.skill_id}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-pos-2",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is True
        assert rsp.fallback_used is True
        assert rsp.skill_id == "builtin:write_test_min"
        assert called == ["superpowers:tdd-workflow", "builtin:write_test_min"]

    # ---- TC-3 · context 白名单注入 ----
    def test_context_sensitive_fields_filtered(
        self, make_executor, project_id: str,
    ) -> None:
        seen: list[dict] = []

        def runner(skill, params, ctx):
            seen.append(ctx)
            return {"ok": True}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-pos-3",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={
                "project_id": project_id,
                "wp_id": "wp-3",
                "api_token": "sk-leak-1",
                "task_board": {"inner": 1},
                "internal_password": "pw",
            },
        )
        rsp = exe.invoke(req)
        assert rsp.success is True
        ctx_seen = seen[0]
        assert "api_token" not in ctx_seen
        assert "internal_password" not in ctx_seen
        assert "task_board" not in ctx_seen
        assert ctx_seen["project_id"] == project_id
        assert ctx_seen["wp_id"] == "wp-3"

    # ---- TC-4 · params 透传 + 结果回包 ----
    def test_params_pass_through_and_result_echoes(
        self, make_executor, project_id: str,
    ) -> None:
        def runner(skill, params, ctx):
            return {"got_params": dict(params), "ctx_pid": ctx["project_id"]}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-pos-4",
            project_id=project_id,
            capability="review_code",
            params={"lang": "python", "strict": True, "list": [1, 2]},
            caller_l1="L1-03",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is True
        assert rsp.result["got_params"] == {"lang": "python", "strict": True, "list": [1, 2]}
        assert rsp.result["ctx_pid"] == project_id
        assert rsp.skill_id == "plugin:python-reviewer"

    # ---- TC-5 · IC-09 审计两次写 ----
    def test_ic09_audit_emits_started_and_finished(
        self, make_executor, ic09_bus, project_id: str,
    ) -> None:
        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-pos-5",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is True
        types = [e.event_type for e in ic09_bus.read_all(project_id)]
        assert "skill_invocation_started" in types
        assert "skill_invocation_finished" in types
