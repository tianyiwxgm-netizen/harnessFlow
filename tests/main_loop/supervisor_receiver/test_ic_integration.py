"""§4 IC 契约集成 · 用真实 Dev-ζ producers → receiver · 闭环验证跨侧 schema 对齐。

- IC-13 SuggestionPusher → SuggestionReceiver.consume_suggestion
- IC-14 RollbackPusher → SuggestionReceiver.consume_rollback
- IC-15 HaltRequester → SuggestionReceiver.consume_halt

这些 TC 比单 consumer 单测更接近生产路径 · 证明 "不改 producer" 原则真实可行。
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltSignal,
    RollbackInbox,
    SuggestionInbox,
)
from app.supervisor.event_sender.halt_requester import MockHardHaltTarget
from app.supervisor.event_sender.schemas import SuggestionLevel

pytestmark = pytest.mark.asyncio


@pytest.fixture
def halt_target() -> MockHardHaltTarget:
    return MockHardHaltTarget()


@pytest.fixture
def receiver(
    pid, event_bus, halt_target, rollback_downstream
) -> SupervisorReceiver:
    return SupervisorReceiver(
        session_pid=pid,
        event_bus=event_bus,
        halt_target=halt_target,
        rollback_downstream=rollback_downstream,
    )


async def test_TC_WP06_IC_INT_601_dev_zeta_suggestion_cmd_consumed_by_receiver(
    receiver, pid, make_suggestion_cmd
) -> None:
    """TC-WP06-IC-INT-601 · Dev-ζ PushSuggestionCommand · 直接包 inbox · receiver 接受。"""
    cmd = make_suggestion_cmd(level=SuggestionLevel.WARN, project_id=pid)
    inbox = SuggestionInbox.from_command(cmd, received_at_ms=100)

    ack = await receiver.consume_suggestion(inbox)

    assert ack.accepted is True
    assert ack.routed_to == AdviceLevel.WARN
    assert ack.suggestion_id == cmd.suggestion_id


async def test_TC_WP06_IC_INT_602_dev_zeta_rollback_cmd_consumed_by_receiver(
    receiver, pid, make_rollback_cmd
) -> None:
    """TC-WP06-IC-INT-602 · Dev-ζ PushRollbackRouteCommand · inbox 包装 · receiver 转发 quality_loop。"""
    cmd = make_rollback_cmd(project_id=pid)
    inbox = RollbackInbox.from_command(cmd, received_at_ms=200)

    ack = await receiver.consume_rollback(inbox)

    assert ack.forwarded is True
    assert ack.route_id == cmd.route_id


async def test_TC_WP06_IC_INT_603_dev_zeta_halt_cmd_consumed_by_receiver(
    receiver, pid, make_halt_cmd, halt_target
) -> None:
    """TC-WP06-IC-INT-603 · Dev-ζ RequestHardHaltCommand · inbox 包装 · receiver halt ≤ SLO。"""
    cmd = make_halt_cmd(project_id=pid)
    signal = HaltSignal.from_command(cmd, received_at_ms=300)

    ack = await receiver.consume_halt(signal)

    assert ack.halted is True
    assert ack.halt_id == cmd.halt_id
    assert ack.latency_ms <= 100
    assert halt_target.halt_call_count == 1
