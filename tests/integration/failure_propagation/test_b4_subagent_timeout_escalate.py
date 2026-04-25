"""B4 · L1-05 子 Agent timeout → L1-01 升级 · 3 TC.

链路:
    L1-05 sub-agent dispatch (IC-04) timeout → fallback → IC-13 push_suggestion
    建议 L1-01 升级处理(level=WARN/SUGG).
"""
from __future__ import annotations

from datetime import UTC, datetime

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


def _make_suggestion(
    *,
    project_id: str,
    suggestion_id: str = "sugg-aaa",
    level: SuggestionLevel = SuggestionLevel.WARN,
    content: str = "subagent timeout · 升级 retry",
) -> PushSuggestionCommand:
    return PushSuggestionCommand(
        suggestion_id=suggestion_id,
        project_id=project_id,
        level=level,
        content=content,
        observation_refs=("obs-timeout-1", "obs-timeout-2"),
        priority=SuggestionPriority.P1,
        ts=datetime.now(UTC).isoformat(),
    )


class TestB4SubagentTimeoutEscalate:
    """B4 · IC-04 timeout → IC-13 升级建议 · 3 TC."""

    async def test_b4_01_timeout_triggers_warn_suggestion_to_l1_01(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B4.1: subagent timeout → IC-13 push WARN suggestion · L1-01 入队收到.

        IC-04 → IC-13 fallback 链.
        """
        consumer = MockSuggestionConsumer()
        pusher = SuggestionPusher(
            session_pid=project_id,
            consumer=consumer,
            event_bus=sup_event_bus,
        )
        cmd = _make_suggestion(project_id=project_id, level=SuggestionLevel.WARN)
        ack = await pusher.push_suggestion(cmd)
        assert ack.enqueued is True
        assert ack.queue_len >= 1
        # 等异步 drain
        import asyncio
        await asyncio.sleep(0.01)
        # consumer 应收到
        assert consumer.delivered_count >= 1
        assert consumer.delivered[0].level == SuggestionLevel.WARN

    async def test_b4_02_cross_pid_suggestion_rejected(
        self,
        project_id: str,
        other_project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B4.2: 跨 pid IC-13 push · 拒 · ValueError E_SUGG_CROSS_PROJECT.

        PM-14: SuggestionPusher.session_pid 锁 · timeout fallback 不能跨 pid 升级.
        """
        consumer = MockSuggestionConsumer()
        pusher = SuggestionPusher(
            session_pid=project_id,
            consumer=consumer,
            event_bus=sup_event_bus,
        )
        cmd = _make_suggestion(project_id=other_project_id)  # 跨 pid
        with pytest.raises(ValueError, match="E_SUGG_CROSS_PROJECT"):
            await pusher.push_suggestion(cmd)
        # consumer 未收
        assert consumer.delivered_count == 0

    async def test_b4_03_audit_emits_l1_07_suggestion_pushed(
        self,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B4.3: IC-13 push 后 IC-09 audit 应有 L1-07:suggestion_pushed 事件.

        L1-05 timeout → L1-07 sense → IC-13 push → IC-09 audit · 完整审计链.
        """
        consumer = MockSuggestionConsumer()
        pusher = SuggestionPusher(
            session_pid=project_id,
            consumer=consumer,
            event_bus=sup_event_bus,
        )
        cmd = _make_suggestion(project_id=project_id, level=SuggestionLevel.SUGG)
        await pusher.push_suggestion(cmd)
        # IC-09 audit 检查
        events = sup_event_bus._events
        push_events = [e for e in events if e.type == "L1-07:suggestion_pushed"]
        assert len(push_events) == 1
        assert push_events[0].payload["level"] == "SUGG"
        assert push_events[0].payload["suggestion_id"] == cmd.suggestion_id
