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

    def test_ic05_ts_field_auto_populated(self):
        """P1-01 · §3.5.2 `ts` required · default_factory 补 UTC ISO-8601 Z."""
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        req = DelegationRequest(
            delegation_id="d", project_id="p1", role="researcher",
            task_brief="A" * 60, context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        assert req.ts and req.ts.endswith("Z")

    def test_ic12_ts_field_auto_populated(self):
        """P1-01 · §3.12.2 `ts` required · default_factory 补 UTC ISO-8601 Z."""
        from app.skill_dispatch.subagent.schemas import CodebaseOnboardingRequest

        req = CodebaseOnboardingRequest(
            delegation_id="d", project_id="p1", repo_path="/tmp/x", kb_write_back=True,
        )
        assert req.ts and req.ts.endswith("Z")

    def test_ic20_ts_field_auto_populated(self):
        """P1-01 · §3.20.2 `ts` required · default_factory 补 UTC ISO-8601 Z."""
        from app.skill_dispatch.subagent.schemas import VerifierRequest

        req = VerifierRequest(
            delegation_id="d", project_id="p1", wp_id="wp1",
            blueprint_slice={}, s4_snapshot={},
            acceptance_criteria=[],
        )
        assert req.ts and req.ts.endswith("Z")


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


# ---------------------------------------------------------------------------
# SDK Client test helpers
# ---------------------------------------------------------------------------


class _FakeSession:
    """In-process fake subagent session · 可配置 behavior."""

    def __init__(self, session_id: str, behavior: str = "success", delay_s: float = 0.0):
        self.session_id = session_id
        self.behavior = behavior   # success / timeout / crash
        self.delay_s = delay_s
        self.terminated = False
        self.kill_force = False
        self.state = "provisioning"


class _FakeAdapter:
    """Fake SDKAdapter for testing · 不依赖真实 Claude SDK."""

    def __init__(self):
        self._sessions: dict[str, _FakeSession] = {}
        self.spawn_count = 0
        self.spawn_failures = 0
        self.sigterm_count = 0
        self.sigkill_count = 0
        # 配置项
        self.fail_first_n_spawns = 0
        self.spawn_behavior = "success"
        self.spawn_delay_s = 0.0

    async def spawn_session(self, *, role, allowed_tools, context, timeout_s):
        import uuid

        self.spawn_count += 1
        if self.spawn_count <= self.fail_first_n_spawns:
            self.spawn_failures += 1
            raise RuntimeError("spawn failed")
        sid = f"sub-{uuid.uuid4().hex[:16]}"
        sess = _FakeSession(
            session_id=sid, behavior=self.spawn_behavior, delay_s=self.spawn_delay_s,
        )
        sess.state = "running"
        self._sessions[sid] = sess
        return sid

    async def await_result(self, session_id: str, timeout_s: float) -> dict:
        import asyncio

        sess = self._sessions[session_id]
        if sess.behavior == "timeout":
            raise asyncio.TimeoutError("fake timeout")
        if sess.behavior == "crash":
            raise RuntimeError("fake crash")
        if sess.delay_s > 0:
            await asyncio.sleep(sess.delay_s)
        sess.state = "completed"
        return {"artifacts": [{"path": "fake.md"}], "final_message": "ok"}

    async def terminate(self, session_id: str, *, force: bool = False) -> None:
        sess = self._sessions.get(session_id)
        if sess is None:
            return
        if force:
            self.sigkill_count += 1
            sess.kill_force = True
        else:
            self.sigterm_count += 1
            sess.terminated = True
        sess.state = "killed"


class TestClaudeSDKClient:
    """Task 04.4 · ClaudeSDKClient · spawn / run / heartbeat / kill lifecycle."""

    async def test_spawn_returns_unique_session_id(self):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient

        adapter = _FakeAdapter()
        client = ClaudeSDKClient(adapter=adapter)
        sids = set()
        for _ in range(100):
            sid = await client.spawn(
                role="researcher", allowed_tools=["Read"],
                context={"project_id": "p1"}, timeout_s=60,
            )
            sids.add(sid)
        assert len(sids) == 100

    async def test_run_returns_artifacts_on_success(self):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient

        adapter = _FakeAdapter()
        client = ClaudeSDKClient(adapter=adapter)
        sid = await client.spawn(
            role="researcher", allowed_tools=["Read"],
            context={"project_id": "p1"}, timeout_s=60,
        )
        result = await client.await_result(session_id=sid, timeout_s=5.0)
        assert result["final_message"] == "ok"
        assert len(result["artifacts"]) == 1

    async def test_run_timeout_triggers_sigterm_then_sigkill(self):
        """超时 · SIGTERM → (5s grace expected · 本测 shrunk) → SIGKILL."""
        import asyncio

        from app.skill_dispatch.subagent.claude_sdk_client import (
            ClaudeSDKClient,
            SubagentTimeoutError,
        )

        adapter = _FakeAdapter()
        adapter.spawn_behavior = "timeout"
        client = ClaudeSDKClient(adapter=adapter, sigterm_grace_s=0.05)
        sid = await client.spawn(
            role="researcher", allowed_tools=["Read"],
            context={"project_id": "p1"}, timeout_s=60,
        )
        with pytest.raises(SubagentTimeoutError):
            await client.await_result(session_id=sid, timeout_s=0.01)
        # 超时后 · client 主动 terminate · 应有 SIGTERM (+ SIGKILL)
        assert adapter.sigterm_count >= 1

    async def test_spawn_retry_once_then_degrade(self):
        """首次 spawn 失败 · retry 1 次 · 再失败 → E_SUB_SPAWN_FAILED."""
        from app.skill_dispatch.subagent.claude_sdk_client import (
            ClaudeSDKClient,
            SpawnFailedError,
        )

        adapter = _FakeAdapter()
        adapter.fail_first_n_spawns = 2   # 2 次都失败
        client = ClaudeSDKClient(adapter=adapter)
        with pytest.raises(SpawnFailedError):
            await client.spawn(
                role="researcher", allowed_tools=["Read"],
                context={"project_id": "p1"}, timeout_s=60,
            )
        assert adapter.spawn_count == 2

    async def test_spawn_retry_succeeds_on_second_attempt(self):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient

        adapter = _FakeAdapter()
        adapter.fail_first_n_spawns = 1
        client = ClaudeSDKClient(adapter=adapter)
        sid = await client.spawn(
            role="researcher", allowed_tools=["Read"],
            context={"project_id": "p1"}, timeout_s=60,
        )
        assert sid.startswith("sub-")
        assert adapter.spawn_count == 2
        assert adapter.spawn_failures == 1

    async def test_allowed_tools_propagated_to_adapter(self):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient

        recorded: dict = {}

        class RecordingAdapter(_FakeAdapter):
            async def spawn_session(self, *, role, allowed_tools, context, timeout_s):
                recorded["allowed_tools"] = allowed_tools
                return await super().spawn_session(
                    role=role, allowed_tools=allowed_tools,
                    context=context, timeout_s=timeout_s,
                )

        client = ClaudeSDKClient(adapter=RecordingAdapter())
        await client.spawn(
            role="verifier", allowed_tools=["Read", "Grep"],
            context={"project_id": "p1"}, timeout_s=120,
        )
        assert recorded["allowed_tools"] == ["Read", "Grep"]

    async def test_kill_idempotent(self):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient

        adapter = _FakeAdapter()
        client = ClaudeSDKClient(adapter=adapter, sigterm_grace_s=0.01)
        sid = await client.spawn(
            role="researcher", allowed_tools=["Read"],
            context={"project_id": "p1"}, timeout_s=60,
        )
        await client.kill(session_id=sid)
        await client.kill(session_id=sid)   # 幂等 · 不 raise
        assert adapter.sigterm_count + adapter.sigkill_count >= 1


class TestDelegator:
    """Task 04.5 · Delegator IC-05/12/20 路由 + 降级链."""

    def _build_delegator(self, adapter, ic09_bus):
        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient
        from app.skill_dispatch.subagent.delegator import Delegator
        from app.skill_dispatch.subagent.resource_limiter import ResourceLimiter

        client = ClaudeSDKClient(adapter=adapter, sigterm_grace_s=0.01)
        limiter = ResourceLimiter(max_concurrent=3, max_queue=10)
        return Delegator(sdk_client=client, limiter=limiter, event_bus=ic09_bus)

    async def test_ic05_dispatch_returns_ack(self, ic09_bus):
        from app.skill_dispatch.subagent.delegator import Delegator
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = DelegationRequest(
            delegation_id="d1", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        ack = await d.delegate_subagent(req)
        assert ack.dispatched is True
        assert ack.subagent_session_id is not None
        assert ack.delegation_id == "d1"

    async def test_ic05_spawn_event_emitted_to_ic09(self, ic09_bus):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = DelegationRequest(
            delegation_id="d2", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        await d.delegate_subagent(req)
        types_seen = [e.event_type for e in ic09_bus.read_all("p1")]
        assert "subagent_spawned" in types_seen

    async def test_ic05_dispatch_latency_under_200ms(self, ic09_bus):
        import time

        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        adapter.spawn_delay_s = 1.0   # run 慢 · 但 dispatch 只等 spawn · 快
        d = self._build_delegator(adapter, ic09_bus)
        req = DelegationRequest(
            delegation_id="d3", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        t0 = time.perf_counter()
        await d.delegate_subagent(req)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 200, f"dispatch SLO breach: {elapsed_ms:.1f}ms"

    async def test_ic05_spawn_retry_exhausted_degrades(self, ic09_bus):
        """spawn 2 次都失败 → E_SUB_SPAWN_FAILED · 返 ack.dispatched=False."""
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        adapter.fail_first_n_spawns = 10  # 总是失败
        d = self._build_delegator(adapter, ic09_bus)
        req = DelegationRequest(
            delegation_id="d4", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        ack = await d.delegate_subagent(req)
        assert ack.dispatched is False
        types_seen = [e.event_type for e in ic09_bus.read_all("p1")]
        assert "subagent_spawn_failed" in types_seen

    async def test_ic05_cross_project_rejected(self, ic09_bus):
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        # schema 层会直接拒（PM-14 mirror check）
        with pytest.raises(ValueError):
            DelegationRequest(
                delegation_id="d",
                project_id="p1",
                role="researcher",
                task_brief="Research best LLM eval frameworks and summarize top 3",
                context_copy={"project_id": "p_other"},
                caller_l1="L1-04",
            )

    async def test_ic12_rejects_invalid_repo_path(self, ic09_bus):
        from app.skill_dispatch.subagent.delegator import OnboardingRepoError
        from app.skill_dispatch.subagent.schemas import CodebaseOnboardingRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = CodebaseOnboardingRequest(
            delegation_id="d", project_id="p1", repo_path="/nonexistent/path",
            kb_write_back=True,
        )
        with pytest.raises(OnboardingRepoError):
            await d.delegate_codebase_onboarding(req)

    async def test_ic12_happy_path_dispatch(self, tmp_project, ic09_bus):
        from app.skill_dispatch.subagent.schemas import CodebaseOnboardingRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = CodebaseOnboardingRequest(
            delegation_id="d_ob", project_id="p1", repo_path=str(tmp_project),
            kb_write_back=True,
        )
        ack = await d.delegate_codebase_onboarding(req)
        assert ack.dispatched is True

    async def test_ic20_verifier_dispatch_with_strict_whitelist(self, ic09_bus):
        from app.skill_dispatch.subagent.schemas import VerifierRequest

        recorded_tools = []

        class RecordingAdapter(_FakeAdapter):
            async def spawn_session(self, *, role, allowed_tools, context, timeout_s):
                recorded_tools.append(list(allowed_tools))
                return await super().spawn_session(
                    role=role, allowed_tools=allowed_tools,
                    context=context, timeout_s=timeout_s,
                )

        adapter = RecordingAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = VerifierRequest(
            delegation_id="d_v", project_id="p1", wp_id="wp1",
            blueprint_slice={"req": "x"}, s4_snapshot={"diff": "y"},
            acceptance_criteria=["A"],
        )
        ack = await d.delegate_verifier(req)
        assert ack.dispatched is True
        assert set(recorded_tools[0]) <= {"Read", "Glob", "Grep", "Bash"}

    async def test_resource_limiter_enforced(self, ic09_bus):
        """超 max_concurrent + max_queue · 排队 · queue 满 raise."""
        import asyncio

        from app.skill_dispatch.subagent.claude_sdk_client import ClaudeSDKClient
        from app.skill_dispatch.subagent.delegator import Delegator
        from app.skill_dispatch.subagent.resource_limiter import (
            ResourceLimiter,
            SessionLimitError,
        )
        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        adapter.spawn_delay_s = 5.0
        client = ClaudeSDKClient(adapter=adapter, sigterm_grace_s=0.01)
        limiter = ResourceLimiter(max_concurrent=1, max_queue=0)   # 超紧
        d = Delegator(sdk_client=client, limiter=limiter, event_bus=ic09_bus)

        async def send(i):
            req = DelegationRequest(
                delegation_id=f"d_{i}", project_id="p1", role="researcher",
                task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
                context_copy={"project_id": "p1"}, caller_l1="L1-04",
            )
            return await d.delegate_subagent(req)

        # 同时发 3 个 · 只有 1 能 dispatched=True · 其余 false
        results = await asyncio.gather(send(1), send(2), send(3), return_exceptions=True)
        dispatched_count = sum(
            1 for r in results if not isinstance(r, Exception) and r.dispatched
        )
        assert dispatched_count <= 1

    async def test_final_report_emitted_via_ic09(self, ic09_bus):
        """dispatch 后台跑完 · emit subagent_final_report · artifacts 齐."""
        import asyncio

        from app.skill_dispatch.subagent.schemas import DelegationRequest

        adapter = _FakeAdapter()
        d = self._build_delegator(adapter, ic09_bus)
        req = DelegationRequest(
            delegation_id="d_final", project_id="p1", role="researcher",
            task_brief="Research best LLM eval frameworks and summarize top 3 in detail",
            context_copy={"project_id": "p1"}, caller_l1="L1-04",
        )
        ack = await d.delegate_subagent(req)
        assert ack.dispatched is True
        # 等后台 task 完
        await asyncio.sleep(0.2)
        types_seen = [e.event_type for e in ic09_bus.read_all("p1")]
        assert "subagent_final_report" in types_seen
