"""TC-WP04-HE-IC15-01..04 · HaltEnforcer × IC-15 consumer 集成(真实 import · WP06 merged)。

目标:
- 本 WP04 HaltEnforcer 实现 HaltTargetProtocol
- 可直接绑到 WP06 IC15Consumer · 端到端 halt 链路正确
- halt latency ≤ 100ms (HRL-05 · IC-15 侧权威测量)
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.supervisor_receiver.schemas import HaltSignal, HaltState
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)


def _make_signal(pid: str, halt_id: str, red_line_id: str) -> HaltSignal:
    cmd = RequestHardHaltCommand(
        halt_id=halt_id,
        project_id=pid,
        red_line_id=red_line_id,
        evidence=HardHaltEvidence(
            observation_refs=("evt-1", "evt-2"),
            confirmation_count=2,
        ),
        require_user_authorization=True,
        ts="2026-04-23T00:00:00Z",
    )
    return HaltSignal.from_command(cmd, received_at_ms=0)


class TestHaltIC15Integration:
    """端到端 · IC-15 consumer → HaltEnforcer → state HALTED。"""

    async def test_TC_WP04_HE_IC15_01_end_to_end_halt_flips_enforcer(self) -> None:
        """TC-WP04-HE-IC15-01 · IC15Consumer.consume → enforcer.halt · state=HALTED。"""
        pid = "pid-e2e"
        enforcer = HaltEnforcer(project_id=pid)
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=enforcer,  # HaltTargetProtocol
            event_bus=EventBusStub(),
        )
        sig = _make_signal(pid, "halt-e2e-001", "IRREVERSIBLE_HALT")

        ack = await consumer.consume(sig)

        assert ack.halted is True
        assert ack.state_before == HaltState.RUNNING
        assert ack.state_after == HaltState.HALTED
        assert enforcer.is_halted() is True
        assert enforcer.active_halt_id == "halt-e2e-001"

    async def test_TC_WP04_HE_IC15_02_halt_latency_under_100ms(self) -> None:
        """TC-WP04-HE-IC15-02 · 端到端 halt latency ≤ 100ms (HRL-05)。"""
        pid = "pid-lat"
        enforcer = HaltEnforcer(project_id=pid)
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=enforcer,
            event_bus=EventBusStub(),
        )
        sig = _make_signal(pid, "halt-lat-001", "DATA_LOSS")
        ack = await consumer.consume(sig)
        assert ack.latency_ms <= 100, f"HRL-05 violated · latency={ack.latency_ms}"
        assert ack.slo_violated is False

    async def test_TC_WP04_HE_IC15_03_halt_idempotent_via_consumer(self) -> None:
        """TC-WP04-HE-IC15-03 · 同 red_line_id 第 2 次 consume → idempotent_hit=True。"""
        pid = "pid-idem"
        enforcer = HaltEnforcer(project_id=pid)
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=enforcer,
            event_bus=EventBusStub(),
        )
        sig1 = _make_signal(pid, "halt-idem-001", "BUDGET_EXCEED")
        sig2 = _make_signal(pid, "halt-idem-002", "BUDGET_EXCEED")  # 同 red_line_id

        a1 = await consumer.consume(sig1)
        a2 = await consumer.consume(sig2)

        assert a1.idempotent_hit is False
        assert a2.idempotent_hit is True
        # enforcer 仍然记 1 次真 halt + 但 history 只 1 条(IC15 consumer 走 cached)
        assert len(enforcer.halt_history) == 1

    async def test_TC_WP04_HE_IC15_04_post_halt_dispatch_rejected(self) -> None:
        """TC-WP04-HE-IC15-04 · halt 后调 enforcer.assert_not_halted → E_TICK_HALTED_REJECT。"""
        from app.main_loop.tick_scheduler.schemas import E_TICK_HALTED_REJECT, TickError

        pid = "pid-post"
        enforcer = HaltEnforcer(project_id=pid)
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=enforcer,
            event_bus=EventBusStub(),
        )
        await consumer.consume(_make_signal(pid, "halt-post-099", "AUDIT_MISS"))

        with pytest.raises(TickError) as exc:
            enforcer.assert_not_halted()
        assert exc.value.error_code == E_TICK_HALTED_REJECT
