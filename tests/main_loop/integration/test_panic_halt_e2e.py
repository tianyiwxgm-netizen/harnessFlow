"""WP07 · panic/halt 100ms e2e 实测 · 跨 L2-01 + L2-06 + 审计链。

铁律:
- panic (IC-17) → PAUSED ≤ 100ms · tick 拒 dispatch
- halt (IC-15) → HALTED ≤ 100ms · tick 拒 dispatch · HRL-05 release blocker
- halt > panic (HALTED 不降级)
- 跨项目 panic/halt 拒绝 (PM-14)

对实测 latency 打印 (P99/max) 供汇报。
"""
from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import HaltSignal
from app.main_loop.tick_scheduler import TickScheduler
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
)
from app.main_loop.tick_scheduler.panic_handler import PanicSignal
from app.main_loop.tick_scheduler.schemas import TickState
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _NoopRollbackDownstream:
    async def consume(self, *args, **kwargs) -> dict:  # noqa: ARG002
        return {"forwarded": True}


# ============================================================
# TC-09 · panic → PAUSED ≤ 100ms (100 次实测 · 取 P99)
# ============================================================


async def test_TC_WP07_PANIC_01_panic_100ms_p99() -> None:
    """100 次 panic · 每次都走 PanicHandler.handle() · P99 latency ≤ 100ms。"""
    pid = "pid-wp07p01"
    latencies_us: list[int] = []

    for i in range(100):
        # 每次创建新 scheduler · 避免 "already paused" 错误码
        sched = TickScheduler.create_default(project_id=pid)
        signal = PanicSignal(
            panic_id=f"panic-p01-{i}",
            project_id=pid,
            user_id="u-test",
            ts=_iso_now(),
        )
        t0 = time.perf_counter_ns()
        result = sched.on_user_panic(signal)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) // 1000)

        assert result.paused is True
        assert sched.current_state == TickState.PAUSED

    latencies_us.sort()
    p50 = latencies_us[len(latencies_us) // 2]
    p99 = latencies_us[int(len(latencies_us) * 0.99)]
    max_us = latencies_us[-1]
    # 硬上限 100ms = 100_000us
    assert p99 < 100_000, (
        f"panic P99={p99}us ≥ 100ms · violates SLO"
    )
    # 打印供汇报
    print(
        f"\n[PANIC P99 e2e · N=100] p50={p50}us p99={p99}us max={max_us}us "
        f"SLO=100000us ratio={max_us/100_000:.4%}"
    )


# ============================================================
# TC-10 · halt (IC-15) → HALTED ≤ 100ms 实测 (HRL-05)
# ============================================================


async def test_TC_WP07_HALT_01_halt_100ms_p99_via_receiver() -> None:
    """100 次走 SupervisorReceiver → HaltEnforcer 全链 halt · P99 ≤ 100ms (HRL-05)。"""
    pid = "pid-wp07h01"
    bus = EventBusStub()
    latencies_ms: list[int] = []

    for i in range(100):
        # 每次 new scheduler + receiver · 避免幂等命中(第二次 halt 也在 100ms · 但测意图是每次新状态)
        sched = TickScheduler.create_default(project_id=pid)
        receiver = SupervisorReceiver(
            session_pid=pid,
            event_bus=bus,
            halt_target=sched.halt_enforcer,
            rollback_downstream=_NoopRollbackDownstream(),
        )
        halt_cmd = RequestHardHaltCommand(
            halt_id=f"halt-h01-{i}",
            project_id=pid,
            red_line_id="redline-test-halt",
            evidence=HardHaltEvidence(
                observation_refs=("ev-h01-1", "ev-h01-2"), confirmation_count=2
            ),
            require_user_authorization=True,
            ts=_iso_now(),
        )
        signal = HaltSignal.from_command(halt_cmd, received_at_ms=0)
        ack = await receiver.consume_halt(signal)

        assert ack.halted is True
        latencies_ms.append(ack.latency_ms)
        # tick 应拒 dispatch
        r = await sched.tick_once()
        assert r.dispatched is False
        assert r.reject_reason == "HALTED"

    latencies_ms.sort()
    p50 = latencies_ms[len(latencies_ms) // 2]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
    max_ms = latencies_ms[-1]
    # HRL-05 铁律
    assert p99 <= 100, f"halt P99={p99}ms > 100ms · HRL-05 violation"
    assert max_ms <= 100, f"halt max={max_ms}ms > 100ms · HRL-05 violation"
    print(
        f"\n[HALT P99 e2e · N=100 via SupervisorReceiver] "
        f"p50={p50}ms p99={p99}ms max={max_ms}ms SLO=100ms"
    )


# ============================================================
# TC-11 · panic + halt 组合 · halt 优先 · resume 不降级
# ============================================================


async def test_TC_WP07_PANIC_HALT_01_halt_wins_panic() -> None:
    """已 HALTED 的 scheduler 再 panic · state 仍 HALTED · resume 不生效。"""
    pid = "pid-wp07ph01"
    bus = EventBusStub()
    dispatcher = StubActionDispatcher()
    sched = TickScheduler.create_default(
        project_id=pid,
        decision_engine=StubDecisionEngine(action={"kind": "invoke_skill"}),
        action_dispatcher=dispatcher,
    )
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=_NoopRollbackDownstream(),
    )

    # halt
    halt_cmd = RequestHardHaltCommand(
        halt_id="halt-ph01",
        project_id=pid,
        red_line_id="redline-irreversible",
        evidence=HardHaltEvidence(
            observation_refs=("ev-1", "ev-2"), confirmation_count=2
        ),
        require_user_authorization=True,
        ts=_iso_now(),
    )
    await receiver.consume_halt(HaltSignal.from_command(halt_cmd, received_at_ms=0))
    assert sched.current_state == TickState.HALTED

    # panic (HALTED 静默 · 不抛 · 不降级)
    sched.on_user_panic(
        PanicSignal(
            panic_id="panic-ph01",
            project_id=pid,
            user_id="u",
            ts=_iso_now(),
        )
    )
    # resume 不生效
    sched.resume_from_panic()
    assert sched.current_state == TickState.HALTED

    # 后续 10 tick 都拒 HALTED
    for _ in range(10):
        r = await sched.tick_once()
        assert r.dispatched is False
        assert r.reject_reason == "HALTED"


# ============================================================
# TC-12 · halt 幂等 · 重复 halt 不改状态 · 每次 latency 都 ≤ 100ms
# ============================================================


async def test_TC_WP07_HALT_02_halt_idempotent_fast() -> None:
    """同 halt_id 重复 halt · idempotent_hit=True · latency 仍 ≤ 100ms。"""
    pid = "pid-wp07h02"
    bus = EventBusStub()
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=_NoopRollbackDownstream(),
    )

    halt_cmd = RequestHardHaltCommand(
        halt_id="halt-h02-same",
        project_id=pid,
        red_line_id="redline-test",
        evidence=HardHaltEvidence(
            observation_refs=("ev-1", "ev-2"), confirmation_count=2
        ),
        require_user_authorization=True,
        ts=_iso_now(),
    )

    # 第一次 halt
    ack1 = await receiver.consume_halt(
        HaltSignal.from_command(halt_cmd, received_at_ms=0)
    )
    assert ack1.halted is True
    assert ack1.latency_ms <= 100

    # 第二次 (同 halt_id)
    ack2 = await receiver.consume_halt(
        HaltSignal.from_command(halt_cmd, received_at_ms=100)
    )
    assert ack2.halted is True
    assert ack2.latency_ms <= 100
    # 幂等 · state 仍 HALTED
    assert sched.current_state == TickState.HALTED
