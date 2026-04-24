"""TC-WP04-AL01..AL20 · AsyncioTickLoop 单 tick + 主逻辑(确定性路径)。"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.main_loop.tick_scheduler.asyncio_loop import (
    AsyncioTickLoop,
    StubActionDispatcher,
    StubDecisionEngine,
    StubStateReader,
)
from app.main_loop.tick_scheduler.deadline_tracker import DeadlineTracker
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler, PanicSignal
from app.main_loop.tick_scheduler.schemas import (
    TICK_INTERVAL_MS_DEFAULT,
    TickEventType,
    TickState,
)


# ------------------------------------------------------------------
# Fake monotonic clock · tracker 用(deterministic drift 测试)
# ------------------------------------------------------------------
@dataclass
class FakeNsClock:
    now_ns: int = 1_000_000_000

    def advance_ms(self, ms: int) -> None:
        self.now_ns += ms * 1_000_000

    def __call__(self) -> int:
        return self.now_ns


# ------------------------------------------------------------------
# Fixture · 预装配 loop
# ------------------------------------------------------------------
@pytest.fixture
def pid() -> str:
    return "pid-loop-001"


@pytest.fixture
def enforcer(pid: str) -> HaltEnforcer:
    return HaltEnforcer(project_id=pid)


@pytest.fixture
def panic_handler(pid: str, enforcer: HaltEnforcer) -> PanicHandler:
    return PanicHandler(project_id=pid, halt_enforcer=enforcer)


@pytest.fixture
def clock() -> FakeNsClock:
    return FakeNsClock()


@pytest.fixture
def tracker(pid: str, clock: FakeNsClock) -> DeadlineTracker:
    return DeadlineTracker(
        project_id=pid,
        interval_ms=TICK_INTERVAL_MS_DEFAULT,
        drift_slo_ms=TICK_INTERVAL_MS_DEFAULT,
        clock_ns=clock,
    )


@pytest.fixture
def make_loop(
    pid: str,
    enforcer: HaltEnforcer,
    panic_handler: PanicHandler,
    tracker: DeadlineTracker,
):
    def _build(
        *,
        engine: StubDecisionEngine | None = None,
        reader: StubStateReader | None = None,
        dispatcher: StubActionDispatcher | None = None,
        interval_ms: int = 100,
    ) -> AsyncioTickLoop:
        return AsyncioTickLoop(
            project_id=pid,
            decision_engine=engine or StubDecisionEngine(),
            state_reader=reader or StubStateReader(),
            action_dispatcher=dispatcher or StubActionDispatcher(),
            halt_enforcer=enforcer,
            panic_handler=panic_handler,
            deadline_tracker=tracker,
            interval_ms=interval_ms,
        )

    return _build


class TestAsyncioTickLoopSingleTick:
    """单 tick 行为 · 不启 loop · tick_once() 驱动。"""

    async def test_TC_WP04_AL01_first_tick_no_op_dispatched_false(
        self, make_loop, tracker: DeadlineTracker, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-AL01 · 首 tick · engine 返 no_op · dispatched=false(non-reject)。"""
        loop = make_loop(engine=StubDecisionEngine(action={"kind": "no_op"}))
        result = await loop.tick_once()
        assert result.dispatched is False
        assert result.action_kind == "no_op"
        assert result.reject_reason is None
        assert result.state == TickState.RUNNING
        assert result.drift_violated is False

    async def test_TC_WP04_AL02_first_tick_invoke_skill_dispatched(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL02 · engine 返 invoke_skill · action_dispatcher 收到。"""
        dispatcher = StubActionDispatcher()
        loop = make_loop(
            engine=StubDecisionEngine(action={"kind": "invoke_skill", "skill": "plan"}),
            dispatcher=dispatcher,
        )
        result = await loop.tick_once()
        assert result.dispatched is True
        assert result.action_kind == "invoke_skill"
        assert len(dispatcher.dispatched) == 1
        assert dispatcher.dispatched[0]["kind"] == "invoke_skill"

    async def test_TC_WP04_AL03_halted_rejects_dispatch_but_tick_continues(
        self, make_loop, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-AL03 · halt 后 tick 继续跑 · 但拒 dispatch(reject_reason=HALTED)。"""
        await enforcer.halt(halt_id="halt-test-001", red_line_id="DATA_LOSS")
        dispatcher = StubActionDispatcher()
        loop = make_loop(
            engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            dispatcher=dispatcher,
        )
        result = await loop.tick_once()
        assert result.dispatched is False
        assert result.reject_reason == "HALTED"
        assert result.state == TickState.HALTED
        assert len(dispatcher.dispatched) == 0
        # tick loop 仍记为 1 tick
        assert loop.tick_seq == 1

    async def test_TC_WP04_AL04_paused_rejects_dispatch(
        self, make_loop, panic_handler: PanicHandler,
    ) -> None:
        """TC-WP04-AL04 · panic 后 · tick 继续跑但拒 dispatch(reject_reason=PAUSED)。"""
        panic_handler.handle(
            PanicSignal(
                panic_id="panic-test-001",
                project_id="pid-loop-001",
                user_id="user-1",
                ts="2026-04-23T00:00:00Z",
                scope="tick",
            )
        )
        dispatcher = StubActionDispatcher()
        loop = make_loop(
            engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            dispatcher=dispatcher,
        )
        result = await loop.tick_once()
        assert result.dispatched is False
        assert result.reject_reason == "PAUSED"
        assert result.state == TickState.PAUSED
        assert len(dispatcher.dispatched) == 0

    async def test_TC_WP04_AL05_decision_exception_does_not_kill_loop(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL05 · decision_engine 抛异常 · tick 完成 · errors 记录 · 不穿透。"""
        engine = StubDecisionEngine(fail_after=0)  # 第一次调用就抛
        loop = make_loop(engine=engine)
        result = await loop.tick_once()
        assert result.dispatched is False
        assert result.reject_reason is not None
        assert result.reject_reason.startswith("EXCEPTION:")
        assert len(loop.errors) == 1
        assert loop.errors[0]["error_type"] == "RuntimeError"

    async def test_TC_WP04_AL06_tick_completed_event_emitted(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL06 · tick_once 产 tick_scheduled / tick_completed 事件。"""
        loop = make_loop(engine=StubDecisionEngine(action={"kind": "no_op"}))
        await loop.tick_once()
        event_types = [e.event_type for e in loop.events]
        assert TickEventType.TICK_SCHEDULED in event_types
        assert TickEventType.TICK_COMPLETED in event_types

    async def test_TC_WP04_AL07_tick_dispatched_event_when_action_sent(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL07 · 真派发 action · tick_dispatched event 产生。"""
        loop = make_loop(
            engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
        )
        await loop.tick_once()
        types = [e.event_type for e in loop.events]
        assert TickEventType.TICK_DISPATCHED in types

    async def test_TC_WP04_AL08_action_rejected_event_when_halted(
        self, make_loop, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-AL08 · HALTED 期间产 action_rejected event。"""
        await enforcer.halt(halt_id="halt-rej-001", red_line_id="AUDIT_MISS")
        loop = make_loop(engine=StubDecisionEngine(action={"kind": "invoke_skill"}))
        await loop.tick_once()
        types = [e.event_type for e in loop.events]
        assert TickEventType.ACTION_REJECTED in types

    async def test_TC_WP04_AL09_drift_violation_when_tick_exceeds_slo(
        self, make_loop, clock: FakeNsClock,
    ) -> None:
        """TC-WP04-AL09 · tick 耗超 interval + slo_ms · drift_violated=true。"""
        engine = StubDecisionEngine(action={"kind": "no_op"})
        loop = make_loop(engine=engine)

        # 在 decide 过程中 · 手动 advance clock > interval + slo (200ms + 1)
        original_decide = engine.decide

        async def slow_decide(ctx):
            clock.advance_ms(250)  # 相对于 start · interval=100 · drift=150 > 100
            return await original_decide(ctx)

        engine.decide = slow_decide  # type: ignore[method-assign]
        result = await loop.tick_once()
        assert result.drift_violated is True
        assert result.drift_ms > 100
        types = [e.event_type for e in loop.events]
        assert TickEventType.TICK_DRIFT_VIOLATED in types

    async def test_TC_WP04_AL10_multiple_ticks_increment_seq(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL10 · 连发 5 次 tick_once · tick_seq=5 · results 5 条。"""
        loop = make_loop()
        for _ in range(5):
            await loop.tick_once()
        assert loop.tick_seq == 5
        assert len(loop.results) == 5
        # 每条 tick_id 唯一
        tick_ids = {r.tick_id for r in loop.results}
        assert len(tick_ids) == 5

    async def test_TC_WP04_AL11_tick_after_resume_dispatches_again(
        self, make_loop, panic_handler: PanicHandler,
    ) -> None:
        """TC-WP04-AL11 · panic → paused → resume → 再 tick 正常派发。"""
        dispatcher = StubActionDispatcher()
        loop = make_loop(
            engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
            dispatcher=dispatcher,
        )
        # 初始 tick 派发
        r0 = await loop.tick_once()
        assert r0.dispatched is True
        # panic
        panic_handler.handle(
            PanicSignal(
                panic_id="panic-abc-001",
                project_id="pid-loop-001",
                user_id="u",
                ts="2026-04-23T00:00:00Z",
            )
        )
        r1 = await loop.tick_once()
        assert r1.dispatched is False
        assert r1.reject_reason == "PAUSED"
        # resume
        panic_handler.resume()
        r2 = await loop.tick_once()
        assert r2.dispatched is True

    async def test_TC_WP04_AL12_state_reader_called_when_running(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL12 · RUNNING 时调 state_reader.read · call_count 递增。"""
        reader = StubStateReader()
        loop = make_loop(reader=reader)
        await loop.tick_once()
        assert reader.call_count == 1
        await loop.tick_once()
        assert reader.call_count == 2

    async def test_TC_WP04_AL13_state_reader_not_called_when_halted(
        self, make_loop, enforcer: HaltEnforcer,
    ) -> None:
        """TC-WP04-AL13 · HALTED 期间 · state_reader 不调(不浪费 IO)。"""
        await enforcer.halt(halt_id="halt-skip-001", red_line_id="AUDIT_MISS")
        reader = StubStateReader()
        loop = make_loop(reader=reader)
        await loop.tick_once()
        assert reader.call_count == 0

    async def test_TC_WP04_AL14_drift_stats_populated(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL14 · 多 tick 后 drift_stats 汇总可读。"""
        loop = make_loop()
        for _ in range(3):
            await loop.tick_once()
        stats = loop.drift_stats
        assert stats["total_ticks"] == 3
        assert stats["violation_count"] == 0
        assert stats["violation_rate"] == 0.0

    async def test_TC_WP04_AL15_constructor_validates(
        self, pid: str, enforcer, panic_handler, tracker,
    ) -> None:
        """TC-WP04-AL15 · 构造参数校验(空 pid · 非正 interval)。"""
        with pytest.raises(ValueError, match="project_id"):
            AsyncioTickLoop(
                project_id="",
                decision_engine=StubDecisionEngine(),
                state_reader=StubStateReader(),
                action_dispatcher=StubActionDispatcher(),
                halt_enforcer=enforcer,
                panic_handler=panic_handler,
                deadline_tracker=tracker,
            )
        with pytest.raises(ValueError, match="interval_ms"):
            AsyncioTickLoop(
                project_id=pid,
                decision_engine=StubDecisionEngine(),
                state_reader=StubStateReader(),
                action_dispatcher=StubActionDispatcher(),
                halt_enforcer=enforcer,
                panic_handler=panic_handler,
                deadline_tracker=tracker,
                interval_ms=0,
            )

    async def test_TC_WP04_AL16_events_ring_buffer_bounded(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL16 · events 环形 buffer(maxlen=1000)- 不爆内存。"""
        loop = make_loop()
        # 一 tick 产 ~3 events(scheduled/dispatched/completed)
        for _ in range(500):
            await loop.tick_once()
        # events 数 ≤ 1000 (maxlen)
        assert len(loop.events) <= 1000


class TestAsyncioTickLoopLifecycle:
    """loop 启停 · 异常隔离。"""

    async def test_TC_WP04_AL17_start_then_stop(self, make_loop) -> None:
        """TC-WP04-AL17 · start() 起 task · stop() graceful 收尾。"""
        loop = make_loop(interval_ms=20)  # 小 interval 快点跑
        await loop.start()
        assert loop.loop_state == TickState.RUNNING
        # 让 loop 跑几次
        import asyncio
        await asyncio.sleep(0.1)
        await loop.stop()
        assert loop.loop_state == TickState.IDLE
        # 至少跑过几次 tick
        assert loop.tick_seq >= 1

    async def test_TC_WP04_AL18_start_twice_raises(self, make_loop) -> None:
        """TC-WP04-AL18 · 重复 start · E_TICK_LOOP_ALREADY_STARTED。"""
        from app.main_loop.tick_scheduler.schemas import E_TICK_LOOP_ALREADY_STARTED, TickError

        loop = make_loop(interval_ms=20)
        await loop.start()
        try:
            with pytest.raises(TickError) as exc:
                await loop.start()
            assert exc.value.error_code == E_TICK_LOOP_ALREADY_STARTED
        finally:
            await loop.stop()

    async def test_TC_WP04_AL19_stop_without_start_raises(self, make_loop) -> None:
        """TC-WP04-AL19 · 未 start 就 stop · E_TICK_LOOP_NOT_RUNNING。"""
        from app.main_loop.tick_scheduler.schemas import E_TICK_LOOP_NOT_RUNNING, TickError

        loop = make_loop()
        with pytest.raises(TickError) as exc:
            await loop.stop()
        assert exc.value.error_code == E_TICK_LOOP_NOT_RUNNING

    async def test_TC_WP04_AL20_engine_exception_logged_loop_continues(
        self, make_loop,
    ) -> None:
        """TC-WP04-AL20 · engine 抛异常 5 tick · loop 照跑 · errors 列表有 5 条。"""
        engine = StubDecisionEngine(fail_after=0)  # 每次都抛
        loop = make_loop(engine=engine, interval_ms=10)
        await loop.start()
        import asyncio
        await asyncio.sleep(0.1)
        await loop.stop()
        assert len(loop.errors) >= 3, "loop 必须继续抓多次异常"
        assert loop.loop_state == TickState.IDLE
