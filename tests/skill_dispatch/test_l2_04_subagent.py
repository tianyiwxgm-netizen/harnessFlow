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


class TestContextScope:
    """Task 04.2 · Context COW + PM-03 隔离 + checksum + 跨 project 拒绝."""

    def test_make_child_context_whitelists_only_public_fields(self):
        from app.skill_dispatch.subagent.context_scope import make_child_context

        parent = {
            "project_id": "p1",
            "wp_id": "wp1",
            "related_artifacts": ["a.md"],
            "dod_exprs": ["x>0"],
            "correlation_id": "c1",
            "task_board": {"secret": 1},    # NOT public
            "api_token": "sk-xxx",           # NOT public
        }
        child, checksum = make_child_context(parent, child_project_id="p1")
        assert child["project_id"] == "p1"
        assert "wp_id" in child
        assert "related_artifacts" in child
        assert "dod_exprs" in child
        assert "correlation_id" in child
        assert "task_board" not in child
        assert "api_token" not in child

    def test_child_context_is_read_only(self):
        """MappingProxyType · 试图写 → TypeError."""
        from app.skill_dispatch.subagent.context_scope import make_child_context

        child, _ = make_child_context({"project_id": "p1"}, child_project_id="p1")
        with pytest.raises(TypeError):
            child["injected"] = "nope"   # type: ignore[index]

    def test_checksum_changes_when_parent_changes(self):
        from app.skill_dispatch.subagent.context_scope import make_child_context

        _, c1 = make_child_context({"project_id": "p1", "wp_id": "wp1"}, child_project_id="p1")
        _, c2 = make_child_context({"project_id": "p1", "wp_id": "wp2"}, child_project_id="p1")
        assert c1 != c2

    def test_checksum_is_sha256_hex(self):
        from app.skill_dispatch.subagent.context_scope import make_child_context

        _, checksum = make_child_context({"project_id": "p1"}, child_project_id="p1")
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_cross_project_delegate_rejected_pm14(self):
        from app.skill_dispatch.subagent.context_scope import (
            ContextIsolationViolation,
            make_child_context,
        )

        with pytest.raises(ContextIsolationViolation):
            make_child_context({"project_id": "p1"}, child_project_id="p2")

    def test_empty_child_project_id_rejected(self):
        from app.skill_dispatch.subagent.context_scope import make_child_context

        with pytest.raises(ValueError, match="project_id"):
            make_child_context({"project_id": "p1"}, child_project_id="")

    def test_context_overflow_rejects_huge_payload(self):
        from app.skill_dispatch.subagent.context_scope import (
            ContextOverflow,
            make_child_context,
        )

        big = {"project_id": "p1", "related_artifacts": ["x" * 1_000_000] * 20}
        with pytest.raises(ContextOverflow):
            make_child_context(big, child_project_id="p1", max_bytes=1024 * 1024)

    def test_verify_checksum_detects_tamper(self):
        from app.skill_dispatch.subagent.context_scope import (
            make_child_context,
            verify_checksum,
        )

        ctx, chk = make_child_context({"project_id": "p1", "wp_id": "wp1"}, child_project_id="p1")
        # Original matches
        assert verify_checksum(dict(ctx), chk) is True
        # Tampered copy
        tampered = dict(ctx)
        tampered["wp_id"] = "altered"
        assert verify_checksum(tampered, chk) is False


class TestResourceLimiter:
    """Task 04.3 · max_concurrent=3 · max_queue=10 · asyncio semaphore."""

    async def test_allows_three_concurrent_slots(self):
        import asyncio

        from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter

        limiter = ResourceLimiter(max_concurrent=3, max_queue=5)
        counter = {"running": 0, "peak": 0}
        lock = asyncio.Lock()

        async def work():
            async with limiter.slot():
                async with lock:
                    counter["running"] += 1
                    counter["peak"] = max(counter["peak"], counter["running"])
                await asyncio.sleep(0.02)
                async with lock:
                    counter["running"] -= 1

        await asyncio.gather(*[work() for _ in range(3)])
        assert counter["peak"] == 3

    async def test_fourth_slot_waits_until_release(self):
        import asyncio
        import time

        from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter

        limiter = ResourceLimiter(max_concurrent=2, max_queue=5)
        durations: list[float] = []

        async def work(delay: float):
            t0 = time.perf_counter()
            async with limiter.slot():
                await asyncio.sleep(delay)
            durations.append(time.perf_counter() - t0)

        await asyncio.gather(work(0.05), work(0.05), work(0.05))
        durations.sort()
        # 第 3 个必然至少等 50ms · 然后自己再跑 50ms
        assert durations[2] > 0.09

    async def test_queue_full_raises_session_limit(self):
        import asyncio

        from app.skill_dispatch.subagent.resource_limiter import (
            ResourceLimiter,
            SessionLimitError,
        )

        limiter = ResourceLimiter(max_concurrent=1, max_queue=1)
        # 1 跑 + 1 排队 = 2 个占位 · 第 3 个立即 raise
        hold_fut: asyncio.Future[None] = asyncio.get_event_loop().create_future()

        async def long_runner():
            async with limiter.slot():
                await hold_fut   # 挂住 · 直到测试最后释放

        async def short_runner():
            async with limiter.slot():
                return True

        t1 = asyncio.create_task(long_runner())
        # 让 t1 进入 slot
        await asyncio.sleep(0.01)
        t2 = asyncio.create_task(short_runner())
        # 让 t2 进入 queue
        await asyncio.sleep(0.01)
        with pytest.raises(SessionLimitError):
            async with limiter.slot():
                pass
        hold_fut.set_result(None)
        await asyncio.gather(t1, t2)

    async def test_slot_released_on_exception(self):
        import asyncio

        from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter

        limiter = ResourceLimiter(max_concurrent=1, max_queue=5)

        async def boom():
            async with limiter.slot():
                raise ValueError("dead")

        try:
            await boom()
        except ValueError:
            pass
        # 如果没释放 · 下一次 slot 会 hang
        async with limiter.slot():
            pass   # 应该立即进入
