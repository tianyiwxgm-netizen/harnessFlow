"""IC-13 消费端 TC · 分级入队 / 幂等 / 非静默 evict / PM-14 / 审计。

对齐 docs/3-2-Solution-TDD §2 / §3 / §4 / §9。
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.ic_13_consumer import IC13Consumer
from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    SuggestionInbox,
)
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import SuggestionLevel

pytestmark = pytest.mark.asyncio


# ------------------------ §2 正向 ------------------------


async def test_TC_WP06_IC13_001_info_audits_only_not_enqueued(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-001 · INFO · 仅审计 · 不入 sugg/warn 队列（§3.1）。"""
    sut = IC13Consumer(session_pid=pid, event_bus=event_bus)
    inbox = make_suggestion_inbox(level=SuggestionLevel.INFO, project_id=pid)

    ack = await sut.consume(inbox)

    assert ack.accepted is True
    assert ack.routed_to == AdviceLevel.INFO
    assert ack.queue_depth_after == 0
    assert sut.queue_depth(AdviceLevel.SUGG) == 0
    assert sut.queue_depth(AdviceLevel.WARN) == 0
    assert sut.counter_snapshot()["info"] == 1


async def test_TC_WP06_IC13_002_sugg_enqueues_into_sugg_queue(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-002 · SUGG · 入 sugg_queue · counter_sugg+1。"""
    sut = IC13Consumer(session_pid=pid, event_bus=event_bus)
    inbox = make_suggestion_inbox(level=SuggestionLevel.SUGG, project_id=pid)

    ack = await sut.consume(inbox)

    assert ack.routed_to == AdviceLevel.SUGG
    assert ack.queue_depth_after == 1
    assert sut.queue_depth(AdviceLevel.SUGG) == 1
    assert sut.queue_depth(AdviceLevel.WARN) == 0
    assert sut.counter_snapshot()["sugg"] == 1


async def test_TC_WP06_IC13_003_warn_enqueues_into_warn_queue(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-003 · WARN · 入 warn_queue · counter_warn+1。"""
    sut = IC13Consumer(session_pid=pid, event_bus=event_bus)
    inbox = make_suggestion_inbox(level=SuggestionLevel.WARN, project_id=pid)

    ack = await sut.consume(inbox)

    assert ack.routed_to == AdviceLevel.WARN
    assert ack.queue_depth_after == 1
    assert sut.queue_depth(AdviceLevel.WARN) == 1
    assert sut.counter_snapshot()["warn"] == 1


async def test_TC_WP06_IC13_004_idempotent_by_suggestion_id(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-004 · 重复 suggestion_id · 返回 cached ack · queue 不再增长。"""
    sut = IC13Consumer(session_pid=pid, event_bus=event_bus)
    inbox = make_suggestion_inbox(level=SuggestionLevel.WARN, project_id=pid)

    ack1 = await sut.consume(inbox)
    # 再消费一次 · 相同 suggestion_id 应返回 cached ack
    ack2 = await sut.consume(inbox)

    assert ack1 == ack2
    assert sut.queue_depth(AdviceLevel.WARN) == 1, "幂等 · 不重复入队"
    assert sut.counter_snapshot()["warn"] == 1


# ------------------------ §3 负向 ------------------------


async def test_TC_WP06_IC13_101_cross_project_rejected(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-101 · project_id != session_pid · 抛 E_SUGG_CROSS_PROJECT。"""
    sut = IC13Consumer(session_pid=pid, event_bus=event_bus)
    other = make_suggestion_inbox(project_id="pid-other")

    with pytest.raises(ValueError, match="E_SUGG_CROSS_PROJECT"):
        await sut.consume(other)

    # 不入队 · 不计数
    assert sut.queue_depth(AdviceLevel.WARN) == 0
    assert sut.counter_snapshot()["warn"] == 0


async def test_TC_WP06_IC13_102_empty_session_pid_rejected(event_bus) -> None:
    """TC-WP06-IC13-102 · session_pid 空字符串 · __post_init__ 抛 E_SUGG_NO_PROJECT_ID。"""
    with pytest.raises(ValueError, match="E_SUGG_NO_PROJECT_ID"):
        IC13Consumer(session_pid="   ", event_bus=event_bus)


async def test_TC_WP06_IC13_105_sugg_queue_overflow_evicts_oldest(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-105 · SUGG queue 满 · evict 最旧 · 新 push ack.accepted=true。"""
    sut = IC13Consumer(
        session_pid=pid, event_bus=event_bus, max_sugg_queue_len=2
    )
    for i in range(3):
        inbox = make_suggestion_inbox(
            level=SuggestionLevel.SUGG,
            project_id=pid,
            suggestion_id=f"sugg-s-{i:03d}",
        )
        await sut.consume(inbox)

    assert sut.queue_depth(AdviceLevel.SUGG) == 2
    remaining_ids = [i.command.suggestion_id for i in sut.peek_queue(AdviceLevel.SUGG)]
    assert remaining_ids == ["sugg-s-001", "sugg-s-002"]
    types = [e.type for e in event_bus._events]
    assert "L1-01:suggestion_evicted" in types


async def test_TC_WP06_IC13_106_warn_queue_overflow_evicts_oldest(
    pid, event_bus, make_suggestion_inbox
) -> None:
    """TC-WP06-IC13-106 · WARN queue 满 · evict 最旧 · 非静默审计 · 新 push ack.accepted=true。"""
    sut = IC13Consumer(
        session_pid=pid, event_bus=event_bus, max_warn_queue_len=2
    )
    first = make_suggestion_inbox(
        level=SuggestionLevel.WARN, project_id=pid, suggestion_id="sugg-001"
    )
    second = make_suggestion_inbox(
        level=SuggestionLevel.WARN, project_id=pid, suggestion_id="sugg-002"
    )
    third = make_suggestion_inbox(
        level=SuggestionLevel.WARN, project_id=pid, suggestion_id="sugg-003"
    )

    await sut.consume(first)
    await sut.consume(second)
    ack3 = await sut.consume(third)

    assert ack3.accepted is True
    assert ack3.queue_depth_after == 2, "满后 evict 最旧 · 入新 · 总深度不变"
    # 最旧的 sugg-001 应被 evict · 仅保留 002 + 003
    remaining_ids = [i.command.suggestion_id for i in sut.peek_queue(AdviceLevel.WARN)]
    assert remaining_ids == ["sugg-002", "sugg-003"]
    # 非静默审计 · event_bus 应记录了 evicted 事件
    types = [e.type for e in event_bus._events]
    assert "L1-01:suggestion_evicted" in types
