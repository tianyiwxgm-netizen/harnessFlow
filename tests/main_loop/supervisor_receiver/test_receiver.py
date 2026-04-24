"""SupervisorReceiver · 唯一 supervisor 网关 · 3 个 consume 方法集成 TC。

- 正向 · 3 个 consume 各自路由到对应 consumer
- 负向 · session_pid 非空 · 3 个 consume 都守 PM-14
- 集成 · 端到端 3 IC 串行消费 · 各自状态独立
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.receiver import SupervisorReceiver
from app.main_loop.supervisor_receiver.schemas import AdviceLevel, HaltState
from app.supervisor.event_sender.halt_requester import MockHardHaltTarget
from app.supervisor.event_sender.schemas import SuggestionLevel

pytestmark = pytest.mark.asyncio


# ------------------------ fixtures ------------------------


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


# ------------------------ §2 正向 ------------------------


async def test_TC_WP06_RECV_001_consume_suggestion_routes_to_ic13(
    receiver, pid, make_suggestion_inbox
) -> None:
    """TC-WP06-RECV-001 · consume_suggestion · WARN 路由到 IC-13 · 入 warn_queue。"""
    inbox = make_suggestion_inbox(level=SuggestionLevel.WARN, project_id=pid)

    ack = await receiver.consume_suggestion(inbox)

    assert ack.accepted is True
    assert ack.routed_to == AdviceLevel.WARN
    assert receiver.queue_depth(AdviceLevel.WARN) == 1


async def test_TC_WP06_RECV_002_consume_rollback_forwards_downstream(
    receiver, pid, make_rollback_inbox
) -> None:
    """TC-WP06-RECV-002 · consume_rollback · 转发 quality_loop · ack.forwarded=true。"""
    inbox = make_rollback_inbox(project_id=pid)

    ack = await receiver.consume_rollback(inbox)

    assert ack.forwarded is True
    assert receiver.is_rollback_forwarded(inbox.command.route_id) is True


async def test_TC_WP06_RECV_003_consume_halt_within_slo(
    receiver, pid, halt_target, make_halt_signal
) -> None:
    """TC-WP06-RECV-003 · consume_halt · latency ≤ SLO · halt_target 调用。"""
    signal = make_halt_signal(project_id=pid)

    ack = await receiver.consume_halt(signal)

    assert ack.halted is True
    assert ack.latency_ms <= 100
    assert ack.state_after == HaltState.HALTED
    assert halt_target.halt_call_count == 1
    assert receiver.is_halted(signal.command.red_line_id) is True


# ------------------------ §3 负向 · PM-14 守护 ------------------------


async def test_TC_WP06_RECV_101_empty_session_pid_rejected(
    event_bus, halt_target, rollback_downstream
) -> None:
    """TC-WP06-RECV-101 · 空 session_pid · __post_init__ 抛 E_SUP_NO_PROJECT_ID。"""
    with pytest.raises(ValueError, match="E_SUP_NO_PROJECT_ID"):
        SupervisorReceiver(
            session_pid="",
            event_bus=event_bus,
            halt_target=halt_target,
            rollback_downstream=rollback_downstream,
        )


async def test_TC_WP06_RECV_102_cross_project_suggestion_rejected(
    receiver, make_suggestion_inbox
) -> None:
    """TC-WP06-RECV-102 · suggestion cross-project · IC-13 拒绝。"""
    inbox = make_suggestion_inbox(project_id="pid-other")
    with pytest.raises(ValueError, match="E_SUGG_CROSS_PROJECT"):
        await receiver.consume_suggestion(inbox)


async def test_TC_WP06_RECV_103_cross_project_rollback_rejected(
    receiver, make_rollback_inbox
) -> None:
    """TC-WP06-RECV-103 · rollback cross-project · IC-14 拒绝。"""
    inbox = make_rollback_inbox(project_id="pid-other")
    with pytest.raises(ValueError, match="E_ROUTE_CROSS_PROJECT"):
        await receiver.consume_rollback(inbox)


async def test_TC_WP06_RECV_104_cross_project_halt_rejected(
    receiver, make_halt_signal, halt_target
) -> None:
    """TC-WP06-RECV-104 · halt cross-project · IC-15 拒绝 · halt_target 不被调。"""
    signal = make_halt_signal(project_id="pid-other")
    with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID"):
        await receiver.consume_halt(signal)
    assert halt_target.halt_call_count == 0


# ------------------------ §8 集成 · 3 IC 串行独立 ------------------------


async def test_TC_WP06_RECV_801_three_ic_independent_state(
    receiver,
    pid,
    make_suggestion_inbox,
    make_rollback_inbox,
    make_halt_signal,
    halt_target,
) -> None:
    """TC-WP06-RECV-801 · 3 IC 串行消费 · counter/queue/halt 状态独立汇聚。"""
    sugg = make_suggestion_inbox(level=SuggestionLevel.WARN, project_id=pid)
    rollback = make_rollback_inbox(project_id=pid)
    halt = make_halt_signal(project_id=pid, red_line_id="redline-integration-1")

    await receiver.consume_suggestion(sugg)
    await receiver.consume_rollback(rollback)
    halt_ack = await receiver.consume_halt(halt)

    # 3 个状态各自独立
    assert receiver.queue_depth(AdviceLevel.WARN) == 1
    assert receiver.is_rollback_forwarded(rollback.command.route_id) is True
    assert receiver.is_halted("redline-integration-1") is True
    assert halt_ack.halted is True
    assert halt_target.halt_call_count == 1


async def test_TC_WP06_RECV_802_counter_snapshot_tracks_ic13_only(
    receiver, pid, make_suggestion_inbox, make_halt_signal
) -> None:
    """TC-WP06-RECV-802 · counter_snapshot 只跟踪 IC-13 · halt 不影响 sugg counter。"""
    await receiver.consume_suggestion(
        make_suggestion_inbox(level=SuggestionLevel.INFO, project_id=pid)
    )
    await receiver.consume_suggestion(
        make_suggestion_inbox(level=SuggestionLevel.SUGG, project_id=pid)
    )
    await receiver.consume_halt(make_halt_signal(project_id=pid))

    snap = receiver.counter_snapshot()
    assert snap == {"info": 1, "sugg": 1, "warn": 0}
