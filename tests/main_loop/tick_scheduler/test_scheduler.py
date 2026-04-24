"""TC-WP04-SC01..SC12 · TickScheduler facade · 端到端装配。"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.state_machine.orchestrator import StateMachineOrchestrator
from app.main_loop.tick_scheduler import (
    PanicSignal,
    StateMachineSnapshotReader,
    TickScheduler,
    TickState,
)
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
)


class TestTickSchedulerFacade:
    """TickScheduler · 公共入口 + 默认工厂装配。"""

    async def test_TC_WP04_SC01_create_default_runs_tick(self) -> None:
        """TC-WP04-SC01 · create_default 工厂 · tick_once 可驱动。"""
        sched = TickScheduler.create_default(project_id="pid-sc-001")
        r = await sched.tick_once()
        assert r.state == TickState.RUNNING
        assert r.drift_violated is False
        assert sched.tick_seq == 1

    async def test_TC_WP04_SC02_on_user_panic_switches_to_paused(self) -> None:
        """TC-WP04-SC02 · on_user_panic → PAUSED ≤ 100ms · current_state=PAUSED。"""
        sched = TickScheduler.create_default(project_id="pid-sc-002")
        sig = PanicSignal(
            panic_id="panic-sc-001",
            project_id="pid-sc-002",
            user_id="u-1",
            ts="2026-04-23T00:00:00Z",
        )
        result = sched.on_user_panic(sig)
        assert result.paused is True
        assert result.panic_latency_ms <= 100
        assert sched.current_state == TickState.PAUSED

    async def test_TC_WP04_SC03_resume_back_to_running(self) -> None:
        """TC-WP04-SC03 · resume_from_panic · PAUSED → RUNNING。"""
        sched = TickScheduler.create_default(project_id="pid-sc-003")
        sched.on_user_panic(
            PanicSignal(
                panic_id="panic-rv-001",
                project_id="pid-sc-003",
                user_id="u",
                ts="2026-04-23T00:00:00Z",
            )
        )
        assert sched.current_state == TickState.PAUSED
        sched.resume_from_panic()
        assert sched.current_state == TickState.RUNNING

    async def test_TC_WP04_SC04_halt_via_enforcer_blocks_dispatch(self) -> None:
        """TC-WP04-SC04 · 直接 halt_enforcer.halt · 后续 tick 拒 dispatch。"""
        sched = TickScheduler.create_default(
            project_id="pid-sc-004",
            decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
        )
        await sched.halt_enforcer.halt(halt_id="halt-sc-001", red_line_id="DATA_LOSS")
        r = await sched.tick_once()
        assert r.dispatched is False
        assert r.reject_reason == "HALTED"
        assert sched.current_state == TickState.HALTED

    async def test_TC_WP04_SC05_state_machine_reader_bridges_wp02(self) -> None:
        """TC-WP04-SC05 · state_reader 用 StateMachineSnapshotReader · 读 WP02 真 state。"""
        orch = StateMachineOrchestrator(
            project_id="pid-sc-005",
            initial_state="INITIALIZED",
        )
        sched = TickScheduler.create_default(
            project_id="pid-sc-005",
            state_machine_orchestrator=orch,
        )
        # loop.state_reader 应为 snapshot reader
        assert isinstance(sched.state_reader, StateMachineSnapshotReader)
        r = await sched.tick_once()
        assert r.state == TickState.RUNNING

    def test_TC_WP04_SC06_snapshot_reader_returns_current_state(self) -> None:
        """TC-WP04-SC06 · snapshot reader.read 返回 WP02 state 字典。"""
        orch = StateMachineOrchestrator(
            project_id="pid-sc-006",
            initial_state="PLANNING",
        )
        reader = StateMachineSnapshotReader(orch)
        data = reader.read("pid-sc-006")
        assert data["current_state"] == "PLANNING"
        assert data["project_id"] == "pid-sc-006"
        assert data["version"] == 0

    def test_TC_WP04_SC07_snapshot_reader_cross_project_returns_unknown(self) -> None:
        """TC-WP04-SC07 · snapshot reader 跨 project · 返回 UNKNOWN(不抛 · 测试友好)。"""
        orch = StateMachineOrchestrator(
            project_id="pid-bound",
            initial_state="INITIALIZED",
        )
        reader = StateMachineSnapshotReader(orch)
        data = reader.read("pid-other")
        assert data["current_state"] == "UNKNOWN"
        assert data.get("cross_project") is True

    async def test_TC_WP04_SC08_lifecycle_start_stop(self) -> None:
        """TC-WP04-SC08 · start / stop 完整 lifecycle · tick_seq > 0。"""
        sched = TickScheduler.create_default(
            project_id="pid-sc-008", interval_ms=20,
        )
        await sched.start()
        assert sched.loop_state == TickState.RUNNING
        await asyncio.sleep(0.08)
        await sched.stop()
        assert sched.loop_state == TickState.IDLE
        assert sched.tick_seq >= 1

    async def test_TC_WP04_SC09_drift_stats_exposed(self) -> None:
        """TC-WP04-SC09 · drift_stats 可读 · 初始 0 · 多 tick 后递增。"""
        sched = TickScheduler.create_default(project_id="pid-sc-009")
        stats0 = sched.drift_stats
        assert stats0["total_ticks"] == 0
        for _ in range(3):
            await sched.tick_once()
        stats1 = sched.drift_stats
        assert stats1["total_ticks"] == 3

    async def test_TC_WP04_SC10_history_observables(self) -> None:
        """TC-WP04-SC10 · halt_history / panic_history 可读。"""
        sched = TickScheduler.create_default(project_id="pid-sc-010")
        sched.on_user_panic(
            PanicSignal(
                panic_id="panic-obs-001",
                project_id="pid-sc-010",
                user_id="u",
                ts="2026-04-23T00:00:00Z",
            )
        )
        assert len(sched.panic_history) == 1
        await sched.halt_enforcer.halt(halt_id="halt-obs-001", red_line_id="AUDIT_MISS")
        assert len(sched.halt_history) == 1

    def test_TC_WP04_SC11_constructor_rejects_empty_pid(self) -> None:
        """TC-WP04-SC11 · 空 project_id 拒(PM-14)。"""
        with pytest.raises(ValueError, match="project_id"):
            TickScheduler.create_default(project_id="")

    async def test_TC_WP04_SC12_halt_persists_across_ticks(self) -> None:
        """TC-WP04-SC12 · halt 后 10 次 tick 都拒 · 验不泄漏 dispatch。"""
        dispatcher = StubActionDispatcher()
        sched = TickScheduler.create_default(
            project_id="pid-sc-012",
            decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            action_dispatcher=dispatcher,
        )
        # 先一次正常派发
        await sched.tick_once()
        assert len(dispatcher.dispatched) == 1
        # halt
        await sched.halt_enforcer.halt(
            halt_id="halt-pers-001", red_line_id="DATA_LOSS",
        )
        # 10 次 tick 全拒
        for _ in range(10):
            r = await sched.tick_once()
            assert r.dispatched is False
            assert r.reject_reason == "HALTED"
        assert len(dispatcher.dispatched) == 1, "halt 后不再新增"
