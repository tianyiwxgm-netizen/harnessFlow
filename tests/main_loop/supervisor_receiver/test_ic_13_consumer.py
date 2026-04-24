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
