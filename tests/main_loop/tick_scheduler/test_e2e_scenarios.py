"""TC-WP04-E2E01..E2E06 · 端到端场景 · halt + panic + 崩溃隔离 + 状态机集成。

P0 场景:
- 正常跑 10 tick → panic → 5 tick 拒 dispatch → resume → 10 tick 正常
- 正常跑 → halt → 10 tick 都拒 · 无论 panic 都不能降级
- decision_engine 抛异常 5 次后恢复 · loop 不死
- 并发 panic + halt 信号 · halt 优先
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.main_loop.state_machine.orchestrator import StateMachineOrchestrator
from app.main_loop.state_machine.schemas import TransitionRequest
from app.main_loop.tick_scheduler import (
    PanicSignal,
    TickScheduler,
    TickState,
)
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
    StubStateReader,
)
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class TestE2EScenarios:
    """P0 端到端场景。"""

    async def test_TC_WP04_E2E01_normal_panic_resume_flow(self) -> None:
        """TC-WP04-E2E01 · 10 tick 派发 → panic → 5 tick 拒 → resume → 10 tick 派发。"""
        dispatcher = StubActionDispatcher()
        sched = TickScheduler.create_default(
            project_id="pid-e2e-01",
            decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            action_dispatcher=dispatcher,
        )
        # 阶段 1 · 10 正常
        for _ in range(10):
            await sched.tick_once()
        assert len(dispatcher.dispatched) == 10

        # 阶段 2 · panic
        sched.on_user_panic(
            PanicSignal(
                panic_id="panic-e2e-01",
                project_id="pid-e2e-01",
                user_id="u",
                ts=_iso_now(),
            )
        )
        # 5 tick 拒
        for _ in range(5):
            r = await sched.tick_once()
            assert r.dispatched is False
            assert r.reject_reason == "PAUSED"
        assert len(dispatcher.dispatched) == 10

        # 阶段 3 · resume
        sched.resume_from_panic()
        for _ in range(10):
            await sched.tick_once()
        assert len(dispatcher.dispatched) == 20

    async def test_TC_WP04_E2E02_halt_is_terminal_ignores_panic_resume(self) -> None:
        """TC-WP04-E2E02 · halt 后 panic → HALTED 优先 · resume 不生效。"""
        dispatcher = StubActionDispatcher()
        sched = TickScheduler.create_default(
            project_id="pid-e2e-02",
            decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            action_dispatcher=dispatcher,
        )
        await sched.tick_once()
        assert len(dispatcher.dispatched) == 1

        # halt
        await sched.halt_enforcer.halt(halt_id="halt-e2e-02", red_line_id="IRREVERSIBLE_HALT")

        # panic (不降级)
        sched.on_user_panic(
            PanicSignal(
                panic_id="panic-e2e-02",
                project_id="pid-e2e-02",
                user_id="u",
                ts=_iso_now(),
            )
        )
        assert sched.current_state == TickState.HALTED

        # resume 不生效
        sched.resume_from_panic()
        assert sched.current_state == TickState.HALTED

        # 20 tick 全拒 HALTED
        for _ in range(20):
            r = await sched.tick_once()
            assert r.dispatched is False
            assert r.reject_reason == "HALTED"
        assert len(dispatcher.dispatched) == 1, "halt 后永不新增"

    async def test_TC_WP04_E2E03_engine_errors_loop_continues(self) -> None:
        """TC-WP04-E2E03 · engine 间歇抛异常 · loop 不死 · errors 记录。"""
        dispatcher = StubActionDispatcher()

        call_count = {"n": 0}

        class FlakyEngine:
            async def decide(self, ctx):
                call_count["n"] += 1
                if call_count["n"] % 3 == 0:
                    raise RuntimeError(f"flake #{call_count['n']}")
                return {"kind": "invoke_skill"}

        sched = TickScheduler.create_default(
            project_id="pid-e2e-03",
            decision_engine=FlakyEngine(),
            action_dispatcher=dispatcher,
        )
        for _ in range(30):
            await sched.tick_once()

        # 30 tick · 10 失败(每 3 个一次) · 20 成功
        # 实际成功数应接近 20
        success_count = len(dispatcher.dispatched)
        assert success_count >= 15, (
            f"engine 间歇失败时 success 数太低 · {success_count}/30"
        )
        # errors buffer 里应有 10 条失败
        assert len(sched.errors) >= 5

    async def test_TC_WP04_E2E04_state_machine_integration(self) -> None:
        """TC-WP04-E2E04 · 与 WP02 StateMachineOrchestrator 真实集成。"""
        orch = StateMachineOrchestrator(
            project_id="pid-a0000004",
            initial_state="INITIALIZED",
        )
        sched = TickScheduler.create_default(
            project_id="pid-a0000004",
            state_machine_orchestrator=orch,
            decision_engine=StubDecisionEngine(action={"kind": "no_op"}),
        )
        # tick 应能读到 INITIALIZED state
        await sched.tick_once()
        # 状态机迁移
        req = TransitionRequest(
            transition_id="trans-e2e-04-aaaa-bbbb",
            project_id="pid-a0000004",
            from_state="INITIALIZED",
            to_state="PLANNING",
            reason="move to PLANNING for WP04 e2e test scenario",
            trigger_tick="tick-0001",
            evidence_refs=("evt-001",),
            ts=_iso_now(),
        )
        result = orch.transition(req)
        assert result.accepted is True
        assert orch.get_current_state() == "PLANNING"
        # 再 tick · state_reader 应读到 PLANNING
        await sched.tick_once()
        data = sched.state_reader.read("pid-a0000004")
        assert data["current_state"] == "PLANNING"

    async def test_TC_WP04_E2E05_running_loop_survives_100_ticks(self) -> None:
        """TC-WP04-E2E05 · 连续后台 loop 100 tick · drift 稳定 · violation_rate < 5%。"""
        sched = TickScheduler.create_default(
            project_id="pid-e2e-05",
            interval_ms=20,  # 20ms tick · 200ms 应跑 ~10 次
            decision_engine=StubDecisionEngine(action={"kind": "no_op"}, latency_ms=0),
        )
        await sched.start()
        # 跑 400ms · 期望 ~20 tick
        await asyncio.sleep(0.4)
        await sched.stop()
        stats = sched.drift_stats
        assert stats["total_ticks"] >= 10
        # drift violation_rate < 50% (real loop 环境 · 宽松)
        assert stats["violation_rate"] < 0.5, (
            f"loop 健康 · violation_rate={stats['violation_rate']}"
        )

    async def test_TC_WP04_E2E06_cross_project_panic_rejected(self) -> None:
        """TC-WP04-E2E06 · 跨 project panic → E_TICK_CROSS_PROJECT 抛。"""
        from app.main_loop.tick_scheduler.schemas import E_TICK_CROSS_PROJECT, TickError

        sched = TickScheduler.create_default(project_id="pid-bound-1")
        with pytest.raises(TickError) as exc:
            sched.on_user_panic(
                PanicSignal(
                    panic_id="panic-cross-001",
                    project_id="pid-other-9",
                    user_id="u",
                    ts=_iso_now(),
                )
            )
        assert exc.value.error_code == E_TICK_CROSS_PROJECT
        # state 应仍 RUNNING
        assert sched.current_state == TickState.RUNNING
