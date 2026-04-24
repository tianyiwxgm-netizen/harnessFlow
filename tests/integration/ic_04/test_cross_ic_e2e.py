"""IC-04 · 跨 IC mini e2e · invoke_skill 触发 IC-09 审计链.

验证 L1-05 → L1-09 的跨 IC 协作:
    - invoke_skill 成功 · IC-09 两次写
    - invoke_skill 失败 · IC-09 两次写 + 失败 payload
    - audit event params_hash 稳定 (两次调用同 params → 同 hash)
"""
from __future__ import annotations

from app.skill_dispatch.invoker.schemas import InvocationRequest


class TestIC04CrossIC09MiniE2E:
    """IC-04 跨 IC-09 · audit event 两次写的完整载荷契约."""

    def test_success_emits_two_audits_with_same_invocation_id(
        self, make_executor, ic09_bus, project_id: str,
    ) -> None:
        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-e2e-succ",
            project_id=project_id,
            capability="write_test",
            params={"k": "v"},
            caller_l1="L1-04",
            context={"project_id": project_id, "wp_id": "w1"},
        )
        exe.invoke(req)
        events = ic09_bus.read_all(project_id)
        assert len(events) >= 2
        # started + finished 都带同 invocation_id
        started = [e for e in events if e.event_type == "skill_invocation_started"]
        finished = [e for e in events if e.event_type == "skill_invocation_finished"]
        assert started and finished
        assert started[0].payload["invocation_id"] == "inv-e2e-succ"
        assert finished[0].payload["invocation_id"] == "inv-e2e-succ"

    def test_failure_emits_finished_with_success_false(
        self, make_executor, ic09_bus, project_id: str,
    ) -> None:
        def runner(skill, params, ctx):
            raise RuntimeError("boom")

        exe = make_executor(runner)
        req = InvocationRequest(
            invocation_id="inv-e2e-fail",
            project_id=project_id,
            capability="write_test",
            params={},
            caller_l1="L1-04",
            context={"project_id": project_id},
        )
        rsp = exe.invoke(req)
        assert rsp.success is False
        # 至少 1 个 finished 事件带 success=False
        finished = [
            e for e in ic09_bus.read_all(project_id)
            if e.event_type == "skill_invocation_finished"
        ]
        assert any(e.payload.get("success") is False for e in finished)

    def test_params_hash_stable_across_invocations(
        self, make_executor, ic09_bus, project_id: str,
    ) -> None:
        """同 params 两次 invoke · IC-09 audit started 载荷 params_hash 一致."""

        def runner(skill, params, ctx):
            return {"ok": True}

        exe = make_executor(runner)
        same_params = {"op": "x", "k": 42, "lst": [1, 2, 3]}

        exe.invoke(InvocationRequest(
            invocation_id="inv-h-1",
            project_id=project_id,
            capability="write_test",
            params=same_params,
            caller_l1="L1-04",
            context={"project_id": project_id},
        ))
        exe.invoke(InvocationRequest(
            invocation_id="inv-h-2",
            project_id=project_id,
            capability="write_test",
            params=same_params,
            caller_l1="L1-04",
            context={"project_id": project_id},
        ))

        started_events = [
            e for e in ic09_bus.read_all(project_id)
            if e.event_type == "skill_invocation_started"
        ]
        hashes = {e.payload.get("params_hash") for e in started_events}
        # 两次都应产生 started · hash 相同
        assert len(started_events) == 2
        assert len(hashes) == 1, f"params_hash 不稳定: {hashes}"
