"""IC-13 SuggestionPusher · fire-and-forget · 3 级 INFO/SUGG/WARN · 队列满时 drop oldest WARN。

关键 TC（按主会话仲裁指令 · ic-contracts §3.13）：
- push_suggestion 正常入队 · 不等 ACK
- INFO/SUGG/WARN 三级分别支持
- project_id 空拒绝 → E_SUGG_NO_PROJECT_ID
- content < 10 字符拒绝 → E_SUGG_CONTENT_TOO_SHORT
- observation_refs 空拒绝 → E_SUGG_NO_OBSERVATION
- 队列满时 drop oldest · ack 带 evicted_suggestion_id
- 仅 drop WARN（最低优先级）· INFO/SUGG 不 drop（业务语义：低打扰）
- 跨 project_id（command.pid != sender session pid）拒绝 → E_SUGG_CROSS_PROJECT
- 非幂等（每条入队 · L1-07 侧自己去重）
"""
from __future__ import annotations

import asyncio

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    PushSuggestionCommand,
    SuggestionLevel,
    SuggestionPriority,
)
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)


pytestmark = pytest.mark.asyncio


def _cmd(
    sid: str = "sugg-abcdef01",
    pid: str = "proj-a",
    level: SuggestionLevel = SuggestionLevel.INFO,
    content: str = "context 80% 建议压缩",
    obs: tuple[str, ...] = ("ev-1",),
    ts: str = "2026-04-23T10:00:00Z",
    priority: SuggestionPriority = SuggestionPriority.P2,
) -> PushSuggestionCommand:
    return PushSuggestionCommand(
        suggestion_id=sid,
        project_id=pid,
        level=level,
        content=content,
        observation_refs=obs,
        priority=priority,
        ts=ts,
    )


@pytest.fixture
def consumer() -> MockSuggestionConsumer:
    return MockSuggestionConsumer()


@pytest.fixture
def bus() -> EventBusStub:
    return EventBusStub()


async def test_push_info_enqueues(consumer: MockSuggestionConsumer, bus: EventBusStub) -> None:
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    ack = await p.push_suggestion(_cmd(level=SuggestionLevel.INFO))
    assert ack.enqueued is True
    assert ack.queue_len >= 1
    assert ack.evicted_suggestion_id is None


async def test_push_sugg_enqueues(consumer: MockSuggestionConsumer, bus: EventBusStub) -> None:
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    ack = await p.push_suggestion(_cmd(level=SuggestionLevel.SUGG))
    assert ack.enqueued is True


async def test_push_warn_enqueues(consumer: MockSuggestionConsumer, bus: EventBusStub) -> None:
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    ack = await p.push_suggestion(_cmd(level=SuggestionLevel.WARN))
    assert ack.enqueued is True


async def test_push_is_fire_and_forget_does_not_wait_consumer(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """fire-and-forget · consumer 尚未 drain 时 ack 已返回。"""
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    # consumer starts paused · push 应立即返回 · consumer 不阻塞 pusher
    consumer.pause()
    ack = await p.push_suggestion(_cmd())
    assert ack.enqueued is True
    # consumer 仍然没拉取 · 队列内积压
    assert p.queue_len() >= 1


async def test_push_rejects_empty_project_id_at_sender_layer(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """pydantic 层会先拒 · 但 sender 二次 guard 确保。"""
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        await p.push_suggestion(_cmd(pid=""))


async def test_push_rejects_cross_project(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    with pytest.raises(ValueError, match="E_SUGG_CROSS_PROJECT"):
        await p.push_suggestion(_cmd(pid="proj-other"))


async def test_queue_overflow_drops_oldest_warn(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    p = SuggestionPusher(
        session_pid="proj-a", consumer=consumer, event_bus=bus, max_queue_len=3
    )
    consumer.pause()
    # 填 3 条 WARN
    ids = []
    for i in range(3):
        ack = await p.push_suggestion(
            _cmd(sid=f"sugg-warn{i:05d}", level=SuggestionLevel.WARN)
        )
        ids.append(ack.suggestion_id)
    # 第 4 条 WARN 会触发 drop oldest
    ack = await p.push_suggestion(
        _cmd(sid="sugg-warn00099", level=SuggestionLevel.WARN)
    )
    assert ack.enqueued is True
    assert ack.evicted_suggestion_id == ids[0]  # oldest
    assert ack.queue_len == 3


async def test_overflow_prefers_dropping_warn_over_info_sugg(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """drop-oldest 策略优先 drop WARN · 若无 WARN 才退化 drop oldest overall。"""
    p = SuggestionPusher(
        session_pid="proj-a", consumer=consumer, event_bus=bus, max_queue_len=3
    )
    consumer.pause()
    await p.push_suggestion(_cmd(sid="sugg-info00000", level=SuggestionLevel.INFO))
    await p.push_suggestion(_cmd(sid="sugg-warn00000", level=SuggestionLevel.WARN))
    await p.push_suggestion(_cmd(sid="sugg-sugg00000", level=SuggestionLevel.SUGG))
    # 加第 4 条 · 队列满 → 应 drop warn00000（虽非 oldest · 但策略优先）
    ack = await p.push_suggestion(
        _cmd(sid="sugg-sugg99999", level=SuggestionLevel.SUGG)
    )
    assert ack.evicted_suggestion_id == "sugg-warn00000"


async def test_emits_ic09_audit_event(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """每次 push 必 append `L1-07:suggestion_pushed` 事件（PRD §8.4 审计链）。"""
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    await p.push_suggestion(_cmd())
    evs = await bus.read_event_stream(project_id="proj-a", types=["L1-07:suggestion_pushed"])
    assert len(evs) == 1
    assert evs[0].payload["suggestion_id"].startswith("sugg-")
    assert evs[0].payload["level"] in {"INFO", "SUGG", "WARN"}


async def test_non_idempotent_same_id_enqueues_twice(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """§3.13.5 · Non-idempotent · L1-07 侧需自己做去重。"""
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    consumer.pause()
    a1 = await p.push_suggestion(_cmd(sid="sugg-dup00001"))
    a2 = await p.push_suggestion(_cmd(sid="sugg-dup00001"))
    assert a1.enqueued is True and a2.enqueued is True
    assert a1.queue_len + 1 == a2.queue_len  # 两次都入队


async def test_consumer_drain_emits_delivered(
    consumer: MockSuggestionConsumer, bus: EventBusStub
) -> None:
    """consumer 未暂停时 · push 后异步 drain · 最终 delivered_count 增长。"""
    p = SuggestionPusher(session_pid="proj-a", consumer=consumer, event_bus=bus)
    await p.push_suggestion(_cmd())
    # 让 fire-and-forget 任务跑
    await asyncio.sleep(0.01)
    assert consumer.delivered_count >= 1


async def test_queue_drain_on_overflow_warn_only() -> None:
    """极端情形：队列只有 WARN 满 · drop oldest WARN。"""
    consumer = MockSuggestionConsumer()
    bus = EventBusStub()
    p = SuggestionPusher(
        session_pid="proj-a", consumer=consumer, event_bus=bus, max_queue_len=2
    )
    consumer.pause()
    await p.push_suggestion(_cmd(sid="sugg-warn00001", level=SuggestionLevel.WARN))
    await p.push_suggestion(_cmd(sid="sugg-warn00002", level=SuggestionLevel.WARN))
    ack = await p.push_suggestion(
        _cmd(sid="sugg-warn00003", level=SuggestionLevel.WARN)
    )
    assert ack.evicted_suggestion_id == "sugg-warn00001"
