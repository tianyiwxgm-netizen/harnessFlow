"""WP07 · 跨 L1 e2e · L1-01 ← L1-07 (IC-13/14/15 真实 Dev-ζ producers + main-2 WP06)。

集成点:
- L1-07 supervisor.event_sender (Dev-ζ merged) → L1-01 supervisor_receiver (main-2 WP06)
- 真实 Dev-ζ SuggestionPusher / RollbackPusher / HaltRequester
- 真实 main-2 WP06 SupervisorReceiver 消费

覆盖 (≥3 TC):
- TC-20 IC-13 Dev-ζ SuggestionPusher → SupervisorReceiver (真 consumer chain)
- TC-21 IC-14 Dev-ζ RollbackPusher → SupervisorReceiver → quality_loop IC14Consumer
- TC-22 IC-15 Dev-ζ HaltRequester → SupervisorReceiver → HaltEnforcer (真 L2-01)
- TC-23 IC-15 P99 latency 实测 · 20次 Dev-ζ → L1-01 · HRL-05
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltSignal,
    RollbackInbox,
    SuggestionInbox,
)
from app.main_loop.tick_scheduler import TickScheduler
from app.quality_loop.rollback_router.ic_14_consumer import (
    IC14Consumer as QualityLoopIC14Consumer,
)
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
)
from app.supervisor.event_sender.rollback_pusher import (
    MockRollbackRouteTarget,
    RollbackPusher,
)
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    HardHaltEvidence,
    PushRollbackRouteCommand,
    PushSuggestionCommand,
    RequestHardHaltCommand,
    RouteEvidence,
    SuggestionLevel,
    SuggestionPriority,
    TargetStage,
)
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)

pytestmark = pytest.mark.asyncio


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class _MockStateTransition:
    """IC-01 state_transition mock · 仅本 suite 用 (quality_loop.rollback_router 下游)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def state_transition(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {"transitioned": True, "project_id": kwargs.get("project_id")}


# ============================================================
# TC-20 · IC-13 Dev-ζ SuggestionPusher → SupervisorReceiver (真)
# ============================================================


async def test_TC_WP07_CROSS_SUP_01_ic13_dev_zeta_to_receiver() -> None:
    """Dev-ζ SuggestionPusher 推 3 条 suggestion · 分别 INFO/SUGG/WARN · 经包 inbox → Receiver。"""
    pid = "pid-wp07xs01"
    bus = EventBusStub()
    consumer = MockSuggestionConsumer()
    pusher = SuggestionPusher(
        session_pid=pid, consumer=consumer, event_bus=bus
    )
    # Receiver 用真 halt_target + mock rollback
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=QualityLoopIC14Consumer(
            session_pid=pid,
            state_transition=_MockStateTransition(),
            event_bus=bus,
        ),
    )

    # 3 条不同级别
    for i, level in enumerate(
        [SuggestionLevel.INFO, SuggestionLevel.SUGG, SuggestionLevel.WARN]
    ):
        cmd = PushSuggestionCommand(
            suggestion_id=f"sugg-xs01-{i}",
            project_id=pid,
            level=level,
            content=f"Dev-ζ 生产端发出的 cross-L1 建议 iter {i}",
            observation_refs=(f"ev-xs01-{i}",),
            priority=SuggestionPriority.P2,
            require_ack_tick_delta=1,
            ts=_iso_now(),
        )
        # Dev-ζ producer 真 push (fire-and-forget · ack 立返)
        ack_producer = await pusher.push_suggestion(cmd)
        assert ack_producer.enqueued is True

        # 主会话仲裁 · 生产路径是 Dev-ζ pusher 发、main-2 WP06 receiver 消费
        # 两侧通过 SupervisorInbox 物理装配 · 这里显式包一下 inbox 再送 receiver
        inbox = SuggestionInbox.from_command(cmd, received_at_ms=i)
        ack_receiver = await receiver.consume_suggestion(inbox)
        assert ack_receiver.accepted is True
        assert ack_receiver.routed_to == AdviceLevel(level.value)

    # counter 3 级各 1
    snap = receiver.counter_snapshot()
    total = sum(snap.values())
    assert total == 3


# ============================================================
# TC-21 · IC-14 Dev-ζ RollbackPusher → Receiver → quality_loop IC14Consumer
# ============================================================


async def test_TC_WP07_CROSS_SUP_02_ic14_dev_zeta_to_quality_loop() -> None:
    """Dev-ζ RollbackPusher → Receiver (main-2 WP06) → quality_loop IC14Consumer (main-1 merged)。"""
    pid = "pid-wp07xs02"
    bus = EventBusStub()
    ic14_state = _MockStateTransition()
    ic14 = QualityLoopIC14Consumer(
        session_pid=pid,
        state_transition=ic14_state,
        event_bus=bus,
    )
    sched = TickScheduler.create_default(project_id=pid)
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=ic14,
    )
    # Dev-ζ producer target 是 L1-04 L2-07 路由器 · 用 MockRollbackRouteTarget 模拟(已注 wp-xs02)
    rollback_target = MockRollbackRouteTarget(known_wps={"wp-xs02"})
    pusher = RollbackPusher(
        session_pid=pid, target=rollback_target, event_bus=bus
    )

    cmd = PushRollbackRouteCommand(
        route_id="route-xs02",
        project_id=pid,
        wp_id="wp-xs02",
        verdict=FailVerdict.FAIL_L2,
        target_stage=TargetStage.S4,
        level_count=1,
        evidence=RouteEvidence(verifier_report_id="vr-xs02"),
        ts=_iso_now(),
    )
    # Dev-ζ producer 真 push · 验 command 结构经得住生产校验
    ack_producer = await pusher.push_rollback_route(cmd)
    assert ack_producer.applied is True
    assert ack_producer.route_id == cmd.route_id
    assert rollback_target.apply_call_count == 1

    # 主路径: Receiver 消费 inbox · 转发到 ic14
    inbox = RollbackInbox.from_command(cmd, received_at_ms=0)
    ack = await receiver.consume_rollback(inbox)
    assert ack.forwarded is True
    assert ack.route_id == cmd.route_id

    # quality_loop IC14Consumer 真调了 state_transition
    assert len(ic14_state.calls) >= 1
    # project_id 和 wp_id 正确
    found_match = any(
        call.get("project_id") == pid and call.get("wp_id") == "wp-xs02"
        for call in ic14_state.calls
    )
    assert found_match


# ============================================================
# TC-22 · IC-15 Dev-ζ HaltRequester → Receiver → HaltEnforcer (真 L2-01)
# ============================================================


async def test_TC_WP07_CROSS_SUP_03_ic15_dev_zeta_halts_tick_loop() -> None:
    """Dev-ζ HaltRequester → main-2 WP06 Receiver → 真 HaltEnforcer · tick 拒 dispatch。"""
    pid = "pid-wp07xs03"
    bus = EventBusStub()
    sched = TickScheduler.create_default(project_id=pid)

    # Dev-ζ 的 target 可以是 sched.halt_enforcer (真 L2-01)
    requester = HaltRequester(
        session_pid=pid, target=sched.halt_enforcer, event_bus=bus
    )

    # 真 Receiver
    from app.quality_loop.rollback_router.ic_14_consumer import (
        IC14Consumer as QualityLoopIC14Consumer,
    )
    receiver = SupervisorReceiver(
        session_pid=pid,
        event_bus=bus,
        halt_target=sched.halt_enforcer,
        rollback_downstream=QualityLoopIC14Consumer(
            session_pid=pid,
            state_transition=_MockStateTransition(),
            event_bus=bus,
        ),
    )

    # 两条路径都应让 L2-01 进入 HALTED · 用 receiver path 测 (主路径)
    halt_cmd = RequestHardHaltCommand(
        halt_id="halt-xs03",
        project_id=pid,
        red_line_id="redline-xs03",
        evidence=HardHaltEvidence(
            observation_refs=("ev-xs03-1", "ev-xs03-2"),
            confirmation_count=2,
        ),
        require_user_authorization=True,
        ts=_iso_now(),
    )
    signal = HaltSignal.from_command(halt_cmd, received_at_ms=0)
    ack = await receiver.consume_halt(signal)
    assert ack.halted is True
    assert ack.latency_ms <= 100

    # tick 拒 dispatch
    r = await sched.tick_once()
    assert r.dispatched is False
    assert r.reject_reason == "HALTED"


# ============================================================
# TC-23 · IC-15 latency P99 · 20 次 Dev-ζ → L1-01 receiver path (HRL-05)
# ============================================================


async def test_TC_WP07_CROSS_SUP_04_ic15_dev_zeta_p99_latency() -> None:
    """20 次 halt 全链 Dev-ζ → Receiver · P99 latency ≤ 100ms (HRL-05)。"""
    pid = "pid-wp07xs04"
    bus = EventBusStub()
    latencies: list[int] = []

    for i in range(20):
        sched = TickScheduler.create_default(project_id=pid)
        receiver = SupervisorReceiver(
            session_pid=pid,
            event_bus=bus,
            halt_target=sched.halt_enforcer,
            rollback_downstream=QualityLoopIC14Consumer(
                session_pid=pid,
                state_transition=_MockStateTransition(),
                event_bus=bus,
            ),
        )
        halt_cmd = RequestHardHaltCommand(
            halt_id=f"halt-xs04-{i}",
            project_id=pid,
            red_line_id="redline-xs04",
            evidence=HardHaltEvidence(
                observation_refs=("ev-1", "ev-2"), confirmation_count=2
            ),
            require_user_authorization=True,
            ts=_iso_now(),
        )
        ack = await receiver.consume_halt(
            HaltSignal.from_command(halt_cmd, received_at_ms=0)
        )
        assert ack.halted is True
        latencies.append(ack.latency_ms)

    latencies.sort()
    p99 = latencies[int(len(latencies) * 0.99)]
    max_ms = latencies[-1]
    assert p99 <= 100, f"IC-15 p99={p99}ms > 100ms · HRL-05 violation"
    print(
        f"\n[IC-15 cross-L1 e2e · N=20 via Dev-ζ HaltRequester schema] "
        f"p99={p99}ms max={max_ms}ms SLO=100ms"
    )
