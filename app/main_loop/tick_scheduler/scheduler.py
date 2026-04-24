"""L2-01 · TickScheduler · 心脏 · 公共入口。

本模块是 WP04 对外的主 facade:
- 组装 HaltEnforcer + PanicHandler + DeadlineTracker + AsyncioTickLoop
- 暴露 5 个 public 方法(对齐 3-1 tech §3 简化子集):
  - start() / stop():       lifecycle
  - on_hard_halt(signal):   IC-15 halt 协议(实际走 HaltEnforcer + ic_15_consumer)
  - on_user_panic(signal):  IC-17 panic 协议 (≤ 100ms PAUSED)
  - tick_once():            单步测试驱动
- 状态只读:
  - current_state:          4 态 TickState
  - drift_stats:            { total_ticks, violation_count, violation_rate }
  - halt_history / panic_history: 审计追溯

与 WP02 state_machine 集成:
- state_reader 可用 StateMachineSnapshotReader (本模块定义) 桥接 StateMachineOrchestrator
- 不侵入 L2-03 · 只读不改

与 WP03 decision_engine 集成:
- decision_engine 用 Protocol · 默认用 StubDecisionEngine
- WP03 merged 后可替换为 app.main_loop.decision_engine.engine.DecisionEngine

HRL-04 铁律:
- tick drift ≤ 100ms P99 (release blocker)
- pytest-benchmark 权威测 · 见 test_tick_drift_bench.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.main_loop.state_machine.orchestrator import StateMachineOrchestrator
from app.main_loop.tick_scheduler.asyncio_loop import (
    ActionDispatcherProtocol,
    AsyncioTickLoop,
    DecisionEngineProtocol,
    ProjectStateReaderProtocol,
    StubActionDispatcher,
    StubDecisionEngine,
    StubStateReader,
)
from app.main_loop.tick_scheduler.deadline_tracker import DeadlineTracker
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicResult,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    TICK_INTERVAL_MS_DEFAULT,
    TickResult,
    TickState,
)


# ------------------------------------------------------------------
# bridge · WP02 state_machine 真实 import
# ------------------------------------------------------------------
class StateMachineSnapshotReader:
    """桥接 WP02 StateMachineOrchestrator → ProjectStateReaderProtocol。

    只读 · 不侵入 L2-03 · 返回 {current_state, version, project_id}。
    """

    def __init__(self, orchestrator: StateMachineOrchestrator) -> None:
        self._orch = orchestrator

    def read(self, project_id: str) -> dict[str, Any]:
        if project_id != self._orch.project_id:
            # PM-14 护栏 · 不抛(测试友好) · 返回空
            return {
                "project_id": project_id,
                "current_state": "UNKNOWN",
                "version": 0,
                "cross_project": True,
            }
        return {
            "project_id": project_id,
            "current_state": self._orch.get_current_state(),
            "version": self._orch.snapshot.version,
        }


# ------------------------------------------------------------------
# TickScheduler · 公共入口 (facade)
# ------------------------------------------------------------------
@dataclass
class TickScheduler:
    """Tick 调度器主入口 · 心脏 · WP04 范围。

    依赖装配:
    - halt_enforcer:      WP04 HaltEnforcer (真)
    - panic_handler:      WP04 PanicHandler (真)
    - deadline_tracker:   WP04 DeadlineTracker (真)
    - decision_engine:    WP03 (concurrent 用 Protocol · 默认 Stub)
    - state_reader:       WP02 真 · 用 StateMachineSnapshotReader 桥接
    - action_dispatcher:  后续 WP · 默认 Stub

    典型工厂用法(端到端):
        sched = TickScheduler.create_default(
            project_id="pid-x",
            interval_ms=100,
        )
        await sched.start()
        ...
        await sched.stop()

    与 IC-15 consumer 集成:
        consumer = IC15Consumer(
            session_pid="pid-x",
            halt_target=sched.halt_enforcer,  # 直接注入
            event_bus=bus,
        )
    """

    project_id: str
    halt_enforcer: HaltEnforcer
    panic_handler: PanicHandler
    deadline_tracker: DeadlineTracker
    decision_engine: DecisionEngineProtocol
    state_reader: ProjectStateReaderProtocol
    action_dispatcher: ActionDispatcherProtocol
    interval_ms: int = TICK_INTERVAL_MS_DEFAULT

    _loop: AsyncioTickLoop = field(init=False)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id required (PM-14)")
        self._loop = AsyncioTickLoop(
            project_id=self.project_id,
            decision_engine=self.decision_engine,
            state_reader=self.state_reader,
            action_dispatcher=self.action_dispatcher,
            halt_enforcer=self.halt_enforcer,
            panic_handler=self.panic_handler,
            deadline_tracker=self.deadline_tracker,
            interval_ms=self.interval_ms,
        )

    # ------------------------------------------------------------------
    # 工厂方法 · 默认装配 (测试常用)
    # ------------------------------------------------------------------
    @classmethod
    def create_default(
        cls,
        *,
        project_id: str,
        interval_ms: int = TICK_INTERVAL_MS_DEFAULT,
        decision_engine: DecisionEngineProtocol | None = None,
        state_reader: ProjectStateReaderProtocol | None = None,
        action_dispatcher: ActionDispatcherProtocol | None = None,
        state_machine_orchestrator: StateMachineOrchestrator | None = None,
    ) -> TickScheduler:
        """默认装配 · 方便测试和端到端集成。

        - state_machine_orchestrator 传入 → 用真 WP02 bridge
        - state_reader 直传 → 用自定义
        - 都不传 → StubStateReader
        """
        halt_enforcer = HaltEnforcer(project_id=project_id)
        panic_handler = PanicHandler(
            project_id=project_id, halt_enforcer=halt_enforcer
        )
        tracker = DeadlineTracker(
            project_id=project_id, interval_ms=interval_ms
        )

        if state_reader is None and state_machine_orchestrator is not None:
            state_reader = StateMachineSnapshotReader(state_machine_orchestrator)
        elif state_reader is None:
            state_reader = StubStateReader()

        return cls(
            project_id=project_id,
            halt_enforcer=halt_enforcer,
            panic_handler=panic_handler,
            deadline_tracker=tracker,
            decision_engine=decision_engine or StubDecisionEngine(),
            state_reader=state_reader,
            action_dispatcher=action_dispatcher or StubActionDispatcher(),
            interval_ms=interval_ms,
        )

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """启动 loop · 非阻塞。"""
        await self._loop.start()

    async def stop(self, timeout_sec: float = 1.0) -> None:
        """停止 loop · graceful。"""
        await self._loop.stop(timeout_sec=timeout_sec)

    async def tick_once(self) -> TickResult:
        """单步驱动(测试/外部调用)。"""
        return await self._loop.tick_once()

    # ------------------------------------------------------------------
    # IC 入口
    # ------------------------------------------------------------------
    def on_user_panic(self, signal: PanicSignal) -> PanicResult:
        """IC-17 user_panic 入口 · sync · ≤ 100ms PAUSED。"""
        return self.panic_handler.handle(signal)

    def resume_from_panic(self) -> None:
        """user 端 authorize · PAUSED → RUNNING(HALTED 不受影响)。"""
        self.panic_handler.resume()

    # ------------------------------------------------------------------
    # 只读状态
    # ------------------------------------------------------------------
    @property
    def current_state(self) -> TickState:
        return self.halt_enforcer.as_tick_state()

    @property
    def loop_state(self) -> TickState:
        return self._loop.loop_state

    @property
    def drift_stats(self) -> dict[str, float | int]:
        return self._loop.drift_stats

    @property
    def tick_seq(self) -> int:
        return self._loop.tick_seq

    @property
    def events(self):
        return self._loop.events

    @property
    def results(self):
        return self._loop.results

    @property
    def errors(self):
        return self._loop.errors

    @property
    def halt_history(self):
        return self.halt_enforcer.halt_history

    @property
    def panic_history(self):
        return self.panic_handler.panic_history


__all__ = [
    "StateMachineSnapshotReader",
    "TickScheduler",
]
