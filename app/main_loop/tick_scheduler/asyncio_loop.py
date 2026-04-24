"""L2-01 · AsyncioTickLoop · 心脏 · 100ms fixed-interval tick loop。

HRL-04 (与 HRL-05 同级 · release blocker) :
- tick drift P99 ≤ 100ms · pytest-benchmark 强校验
- 违反视为 release blocker · 同 IC-15 halt 铁律

loop 主逻辑(对齐 3-1 tech §6.1 scheduling_loop):

    while running:
        budget = tracker.start_tick(tick_id)
        if halt_enforcer.is_halted():
            # 拒 action · 继续 tick (消费端驱动 · loop 仍跑)
            await sleep_until_next_tick(budget)
            continue
        try:
            state = read_project_state()
            action = await decision_engine.decide(state, ctx)
            if can_dispatch():
                await dispatch(action)
        except Exception as e:
            # 永不让异常穿透 loop (tick 必须继续)
            emit_audit('tick_error', e)
        violation = tracker.end_tick(budget)
        if violation: emit_audit('tick_drift_violated', violation)
        await sleep_until_next_tick(budget)

实现要点:
- `sleep_until_next_tick`: 基于 deadline_ns 补偿 · 保证 fixed-interval
- 异常隔离: 单 tick 异常不中断 loop
- 停机: cancel 支持 graceful shutdown
- 可单步驱动: tick_once() 供测试 deterministic 单 tick

DecisionEngine 用 Protocol mock:
- 真的 WP03 实现 concurrent · 这里只绑 Protocol
- test 用 StubDecisionEngine 精细控制 latency/result
"""
from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.main_loop.tick_scheduler.deadline_tracker import DeadlineTracker
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_LOOP_ALREADY_STARTED,
    E_TICK_LOOP_NOT_RUNNING,
    TICK_INTERVAL_MS_DEFAULT,
    TickError,
    TickEvent,
    TickEventType,
    TickResult,
    TickState,
)


# ------------------------------------------------------------------
# Protocol · DecisionEngine 契约 (WP03 将实现)
# ------------------------------------------------------------------
class DecisionEngineProtocol(Protocol):
    """L2-02 DecisionEngine 契约 · WP04 用 Protocol mock 解耦。

    async def decide(ctx) -> ChosenAction (精简版返回 dict 即可)
    """

    async def decide(self, ctx: dict[str, Any]) -> dict[str, Any]: ...


class ProjectStateReaderProtocol(Protocol):
    """项目 state 读取器 · 可挂 app.main_loop.state_machine.orchestrator。

    读 current state (7 态 · 不改 state)。
    """

    def read(self, project_id: str) -> dict[str, Any]: ...


class ActionDispatcherProtocol(Protocol):
    """action 下发器 · WP04 阶段 mock · 后续接真 tool/skill 调用。"""

    async def dispatch(self, action: dict[str, Any]) -> None: ...


# ------------------------------------------------------------------
# Stub 实现 · 供测试即插即用
# ------------------------------------------------------------------
class StubDecisionEngine:
    """测试用 · 返回固定 action + 可控 latency。"""

    def __init__(
        self,
        action: dict[str, Any] | None = None,
        latency_ms: int = 0,
        fail_after: int | None = None,
    ) -> None:
        self.action = action or {"kind": "no_op", "params": {}}
        self.latency_ms = latency_ms
        self.fail_after = fail_after
        self.call_count = 0

    async def decide(self, ctx: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        self.call_count += 1
        if self.fail_after is not None and self.call_count > self.fail_after:
            raise RuntimeError(f"stub failure after {self.fail_after}")
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)
        return dict(self.action)


class StubStateReader:
    """测试用 · 返回固定 state dict。"""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {"current_state": "RUNNING", "version": 0}
        self.call_count = 0

    def read(self, project_id: str) -> dict[str, Any]:
        self.call_count += 1
        return {"project_id": project_id, **self.state}


class StubActionDispatcher:
    """测试用 · 收集 dispatched action · 可选 latency。"""

    def __init__(self, latency_ms: int = 0) -> None:
        self.dispatched: list[dict[str, Any]] = []
        self.latency_ms = latency_ms

    async def dispatch(self, action: dict[str, Any]) -> None:
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)
        self.dispatched.append(action)


# ------------------------------------------------------------------
# 主 loop 类
# ------------------------------------------------------------------
@dataclass
class AsyncioTickLoop:
    """asyncio fixed-interval tick loop · 100ms 心脏。

    用法:
        loop = AsyncioTickLoop(
            project_id="pid-x",
            interval_ms=100,
            decision_engine=engine,
            state_reader=reader,
            action_dispatcher=dispatcher,
            halt_enforcer=halt_enforcer,
            panic_handler=panic_handler,
            deadline_tracker=tracker,
        )
        await loop.start()        # 非阻塞 · 后台 task
        # ...
        await loop.stop()

    单步测试:
        result = await loop.tick_once()  # 一 iteration · 含测 drift
    """

    project_id: str
    decision_engine: DecisionEngineProtocol
    state_reader: ProjectStateReaderProtocol
    action_dispatcher: ActionDispatcherProtocol
    halt_enforcer: HaltEnforcer
    panic_handler: PanicHandler
    deadline_tracker: DeadlineTracker
    interval_ms: int = TICK_INTERVAL_MS_DEFAULT

    # 运行态
    _state: TickState = field(default=TickState.IDLE, init=False)
    _tick_seq: int = field(default=0, init=False)
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _stop_event: asyncio.Event | None = field(default=None, init=False)

    # 审计 · 环形 buffer 记最近 N 条
    _events: deque[TickEvent] = field(
        default_factory=lambda: deque(maxlen=1000), init=False
    )
    _results: deque[TickResult] = field(
        default_factory=lambda: deque(maxlen=1000), init=False
    )
    # 异常记录 · 非致命(loop 继续)
    _errors: list[dict[str, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id required (PM-14)")
        if self.interval_ms <= 0:
            raise ValueError(f"interval_ms must be positive · got {self.interval_ms}")

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """启动 loop · 后台 task · 非阻塞返回。"""
        if self._task is not None and not self._task.done():
            raise TickError(
                error_code=E_TICK_LOOP_ALREADY_STARTED,
                message="loop already running",
                project_id=self.project_id,
            )
        self._state = TickState.RUNNING
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            self._run_forever(), name=f"tick_loop:{self.project_id}"
        )

    async def stop(self, timeout_sec: float = 1.0) -> None:
        """停止 loop · graceful · 等 task 收尾。"""
        if self._task is None:
            raise TickError(
                error_code=E_TICK_LOOP_NOT_RUNNING,
                message="loop not running",
                project_id=self.project_id,
            )
        assert self._stop_event is not None
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=timeout_sec)
        except TimeoutError:  # pragma: no cover - 防御
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
        finally:
            self._task = None
            self._state = TickState.IDLE

    async def _run_forever(self) -> None:
        """后台主 loop · stop_event 触发退出。"""
        assert self._stop_event is not None
        try:
            while not self._stop_event.is_set():
                await self.tick_once()
                # 补偿 sleep: 用 tracker 的 deadline - now
                await self._sleep_to_next_tick()
        except asyncio.CancelledError:  # pragma: no cover - 防御
            return

    async def _sleep_to_next_tick(self) -> None:
        """sleep 直到下个 tick 应开始 · 基于 interval_ms 补偿。

        最朴素的 fixed-interval 实现:
        - 本 iteration 开销 latency_ms (tracker 知道)
        - sleep_ms = max(0, interval_ms - last_iteration_cost)
        - 但更简单的做法:始终 sleep = interval_ms (期望 iteration 很快 ≤ 1ms)
          且 tracker 会捕获 drift · 超阈自告警
        """
        # 对齐 tech §6.1 · 最朴素安全实现: sleep(interval_ms)
        # 更复杂的补偿算法放 WP 后续优化 · 当前关键是 drift 可测
        await asyncio.sleep(self.interval_ms / 1000.0)

    # ------------------------------------------------------------------
    # single tick · 可独立调
    # ------------------------------------------------------------------
    async def tick_once(self) -> TickResult:
        """单 tick · 返回 TickResult(含 drift_ms + violation 标志)。

        主逻辑(对齐 §6.1):
        1. 分配 TickBudget(tracker.start_tick)
        2. 头部判 halt/paused · HALTED 拒 action · tick 仍跑(记 action_rejected)
        3. 读 project state (state_reader)
        4. 调 decision_engine.decide(ctx)
        5. 判 can_dispatch · PAUSED/HALTED 拒 dispatch
        6. dispatch action (如果允许)
        7. tracker.end_tick · 测 drift · 产 violation event
        """
        self._tick_seq += 1
        tick_id = f"tick-{uuid.uuid4().hex[:16]}"

        budget = self.deadline_tracker.start_tick(tick_id)
        state_at_start = self.halt_enforcer.as_tick_state()

        self._emit_event(
            TickEvent(
                event_type=TickEventType.TICK_SCHEDULED,
                tick_id=tick_id,
                project_id=self.project_id,
                ts_ns=budget.started_at_ns,
                state_after=state_at_start,
            )
        )

        dispatched = False
        action_kind: str | None = None
        reject_reason: str | None = None

        try:
            # HALTED: loop 继续跑 · 但拒一切 dispatch
            # PAUSED: 同理 · 等 resume
            if self.halt_enforcer.is_halted():
                reject_reason = "HALTED"
            elif state_at_start == TickState.PAUSED:
                reject_reason = "PAUSED"
            else:
                # 读 state
                project_state = self.state_reader.read(self.project_id)
                # 调 decision_engine
                action = await self.decision_engine.decide(
                    {
                        "project_id": self.project_id,
                        "tick_id": tick_id,
                        "project_state": project_state,
                    }
                )
                action_kind = str(action.get("kind", "no_op"))

                # 派发前再判一次 (panic 可能在 decide 期间抵达)
                try:
                    self.halt_enforcer.assert_can_dispatch()
                except TickError as e:
                    reject_reason = e.error_code
                    dispatched = False
                else:
                    if action_kind == "no_op":
                        # no_op 不派发 · 但不算 reject · dispatched=False reject_reason=None
                        dispatched = False
                    else:
                        await self.action_dispatcher.dispatch(action)
                        dispatched = True
                        self._emit_event(
                            TickEvent(
                                event_type=TickEventType.TICK_DISPATCHED,
                                tick_id=tick_id,
                                project_id=self.project_id,
                                ts_ns=time.perf_counter_ns(),
                                extra={"action_kind": action_kind},
                            )
                        )
        except Exception as e:  # noqa: BLE001  - loop 永不穿透
            self._errors.append(
                {
                    "tick_id": tick_id,
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "ts_ns": time.perf_counter_ns(),
                }
            )
            reject_reason = f"EXCEPTION:{type(e).__name__}"

        # 结束 · 测 drift
        violation = self.deadline_tracker.end_tick(
            budget, context={"reject_reason": reject_reason}
        )
        latency_ms = self.deadline_tracker.measure_latency_ms(budget)
        drift_ms = max(0, latency_ms - budget.interval_ms)
        drift_violated = violation is not None

        if violation is not None:
            self._emit_event(
                TickEvent(
                    event_type=TickEventType.TICK_DRIFT_VIOLATED,
                    tick_id=tick_id,
                    project_id=self.project_id,
                    ts_ns=violation.ts_ns,
                    latency_ms=latency_ms,
                    drift_ms=violation.drift_ms,
                    extra={"slo_ms": budget.drift_slo_ms},
                )
            )

        state_after = self.halt_enforcer.as_tick_state()
        result = TickResult(
            tick_id=tick_id,
            dispatched=dispatched,
            action_kind=action_kind,
            latency_ms=latency_ms,
            drift_ms=drift_ms,
            drift_violated=drift_violated,
            state=state_after,
            reject_reason=reject_reason,
        )
        self._results.append(result)

        self._emit_event(
            TickEvent(
                event_type=TickEventType.TICK_COMPLETED,
                tick_id=tick_id,
                project_id=self.project_id,
                ts_ns=time.perf_counter_ns(),
                state_before=state_at_start,
                state_after=state_after,
                latency_ms=latency_ms,
                drift_ms=drift_ms,
                extra={"dispatched": dispatched, "action_kind": action_kind},
            )
        )

        if reject_reason and reject_reason in {"HALTED", "PAUSED"}:
            self._emit_event(
                TickEvent(
                    event_type=TickEventType.ACTION_REJECTED,
                    tick_id=tick_id,
                    project_id=self.project_id,
                    ts_ns=time.perf_counter_ns(),
                    state_before=state_at_start,
                    state_after=state_after,
                    extra={"reject_reason": reject_reason},
                )
            )

        return result

    # ------------------------------------------------------------------
    # observability
    # ------------------------------------------------------------------
    def _emit_event(self, event: TickEvent) -> None:
        self._events.append(event)

    @property
    def current_state(self) -> TickState:
        return self.halt_enforcer.as_tick_state()

    @property
    def loop_state(self) -> TickState:
        return self._state

    @property
    def tick_seq(self) -> int:
        return self._tick_seq

    @property
    def events(self) -> tuple[TickEvent, ...]:
        return tuple(self._events)

    @property
    def results(self) -> tuple[TickResult, ...]:
        return tuple(self._results)

    @property
    def errors(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._errors)

    @property
    def drift_stats(self) -> dict[str, float | int]:
        return {
            "total_ticks": self.deadline_tracker.total_ticks,
            "violation_count": self.deadline_tracker.violation_count,
            "violation_rate": self.deadline_tracker.violation_rate,
        }


__all__ = [
    "ActionDispatcherProtocol",
    "AsyncioTickLoop",
    "DecisionEngineProtocol",
    "ProjectStateReaderProtocol",
    "StubActionDispatcher",
    "StubDecisionEngine",
    "StubStateReader",
]
