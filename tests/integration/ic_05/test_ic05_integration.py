"""IC-05 · delegate_subagent 集成测试 · 6 TC.

覆盖 (对齐 ic-contracts.md §3.5 + WP04 任务表):
    TC-1 正向: dispatch=True · subagent_session_id 透出 · spawned 事件
    TC-2 重复 delegation_id: 上游去重 (本 IC 接 stub 不强制 · 但允许多次派 · 各自独立 id)
    TC-3 能力空 → schema 拒绝 · context 缺 project_id
    TC-4 spawn 失败 (1 次) → 重试 OK (limiter slot 不泄漏)
    TC-5 错误码 E_SUB_SPAWN_FAILED · 2 次失败 → dispatched=False + spawn_failed 事件
    TC-6 SLO · dispatch ≤ 200ms 硬约束 (§3.5 SLO)
"""
from __future__ import annotations

import asyncio
import time
from contextlib import suppress

import pytest

from app.skill_dispatch.subagent.schemas import DelegationRequest

from .conftest import FakeAdapter, FakeBus, run_async


class TestIC05Integration:
    """IC-05 集成 · Delegator + ResourceLimiter + FakeAdapter 全链."""

    # ---- TC-1 · 正向: dispatched=True + subagent_session_id ----
    def test_dispatch_returns_session_id_and_emits_spawned(
        self,
        delegator,
        make_request,
        fake_bus: FakeBus,
        fake_adapter: FakeAdapter,
        project_id: str,
    ) -> None:
        req = make_request(delegation_id="del-tc1-pos", role="researcher")

        ack = run_async(delegator.delegate_subagent(req))

        assert ack.dispatched is True
        assert ack.delegation_id == "del-tc1-pos"
        assert ack.subagent_session_id is not None
        # IC-05 §3.5.3 subagent_session_id format: prefix sub-
        assert ack.subagent_session_id.startswith("sub-")

        # spawned 事件 emit · payload 含 delegation_id + role
        spawned = fake_bus.by_type("subagent_spawned")
        assert len(spawned) == 1
        assert spawned[0]["payload"]["delegation_id"] == "del-tc1-pos"
        assert spawned[0]["payload"]["role"] == "researcher"
        assert spawned[0]["project_id"] == project_id
        assert spawned[0]["l1"] == "L1-05"

        # adapter spawn 1 次 · 角色对齐
        assert len(fake_adapter.spawn_calls) == 1
        assert fake_adapter.spawn_calls[0]["role"] == "researcher"

    # ---- TC-2 · 重复 delegation_id: 各次独立派 (Non-idempotent · §3.5.6) ----
    def test_repeated_delegation_id_dispatches_each_time(
        self,
        delegator,
        make_request,
        fake_bus: FakeBus,
    ) -> None:
        """IC-05 是 Non-idempotent · 上游去重 · 本 dispatcher 不强制."""
        r1 = make_request(delegation_id="del-tc2-dup", role="coder")
        r2 = make_request(delegation_id="del-tc2-dup", role="coder")

        ack1 = run_async(delegator.delegate_subagent(r1))
        ack2 = run_async(delegator.delegate_subagent(r2))

        assert ack1.dispatched is True
        assert ack2.dispatched is True
        # 各自独立 session_id
        assert ack1.subagent_session_id != ack2.subagent_session_id
        # 两次 spawned 事件
        assert len(fake_bus.by_type("subagent_spawned")) == 2

    # ---- TC-3 · 负向 · context_copy 跨 project_id (PM-14) ----
    def test_context_copy_pid_mismatch_rejected_at_schema(
        self,
        project_id: str,
        task_brief: str,
    ) -> None:
        """schema 层 PM-14 自检 · ctx.project_id != top.project_id → ValueError."""
        with pytest.raises(ValueError, match="project_id mismatch"):
            DelegationRequest(
                delegation_id="del-tc3-neg",
                project_id=project_id,
                role="researcher",
                task_brief=task_brief,
                context_copy={"project_id": "proj-other"},
                caller_l1="L1-04",
            )

    # ---- TC-4 · spawn 失败 1 次 → 重试 OK · slot 无泄 ----
    def test_spawn_retry_once_then_success(
        self,
        delegator,
        make_request,
        fake_adapter: FakeAdapter,
        fake_bus: FakeBus,
    ) -> None:
        fake_adapter.spawn_fail_first_n = 1  # 1 次失败 · 第 2 次 OK
        req = make_request(delegation_id="del-tc4-retry", role="reviewer")

        ack = run_async(delegator.delegate_subagent(req))

        # ClaudeSDKClient 内置 retry 1 次 · MAX_SPAWN_ATTEMPTS=2
        assert ack.dispatched is True
        assert ack.subagent_session_id is not None
        # adapter 收到 2 次 spawn (1 fail + 1 ok)
        assert len(fake_adapter.spawn_calls) == 2

        # spawn_failed 不发 (因为最终成功)
        assert len(fake_bus.by_type("subagent_spawn_failed")) == 0
        assert len(fake_bus.by_type("subagent_spawned")) == 1

    # ---- TC-5 · 2 次 spawn 失败 → dispatched=False + spawn_failed 事件 ----
    def test_spawn_failed_twice_returns_dispatched_false(
        self,
        delegator,
        make_request,
        fake_adapter: FakeAdapter,
        fake_bus: FakeBus,
    ) -> None:
        fake_adapter.spawn_fail_first_n = 5  # 远超 retry 上限
        req = make_request(delegation_id="del-tc5-fail", role="researcher")

        ack = run_async(delegator.delegate_subagent(req))

        assert ack.dispatched is False
        assert ack.subagent_session_id is None
        # delegation_id 仍透出 · 供上游审计
        assert ack.delegation_id == "del-tc5-fail"

        failed_events = fake_bus.by_type("subagent_spawn_failed")
        assert len(failed_events) == 1
        assert failed_events[0]["payload"]["delegation_id"] == "del-tc5-fail"

        # 没有 spawned 事件
        assert len(fake_bus.by_type("subagent_spawned")) == 0

    # ---- TC-6 · SLO: dispatch ≤ 200ms (§3.5 dispatch SLO) ----
    def test_slo_dispatch_within_200ms(
        self,
        delegator,
        make_request,
    ) -> None:
        """IC-05 SLO §3.5 · Dispatch ≤ 200ms · 本测在内存 fake adapter 远快于阈值."""
        req = make_request(delegation_id="del-tc6-slo", role="researcher")

        t0 = time.perf_counter()
        ack = run_async(delegator.delegate_subagent(req))
        dispatch_ms = (time.perf_counter() - t0) * 1000.0

        assert ack.dispatched is True
        # IC-05 SLO 200ms 硬上限 · fake adapter 路径应远低于此
        assert dispatch_ms < 200.0, f"IC-05 dispatch SLO 超时 {dispatch_ms:.1f}ms"
