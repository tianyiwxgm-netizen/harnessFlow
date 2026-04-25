"""IC-13 集成 fixtures · 真实 SuggestionPusher + MockSuggestionConsumer.

铁律:
- 真实 import `app.supervisor.event_sender.suggestion_pusher`
- 真实 EventBusStub (supervisor 自带 · IC-09 审计 stub) 验证 suggestion_pushed 落 audit
- pusher 内部 fire-and-forget · asyncio.create_task drain
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


@pytest.fixture
def project_id() -> str:
    return "proj-ic13"


@pytest.fixture
def other_project_id() -> str:
    return "proj-ic13-other"


@pytest.fixture
def supervisor_bus() -> EventBusStub:
    """L1-07 自有 EventBusStub · 内存版 IC-09 审计."""
    return EventBusStub()


@pytest.fixture
def consumer() -> MockSuggestionConsumer:
    return MockSuggestionConsumer()


@pytest.fixture
def pusher(
    project_id: str,
    consumer: MockSuggestionConsumer,
    supervisor_bus: EventBusStub,
) -> SuggestionPusher:
    return SuggestionPusher(
        session_pid=project_id,
        consumer=consumer,
        event_bus=supervisor_bus,
    )


@pytest.fixture
def make_suggestion_command(project_id: str):
    """工厂 · 给定 SDP id / reason → PushSuggestionCommand · 默认 level=WARN."""

    def _mk(
        *,
        suggestion_id: str,
        sdp_id: str,
        content: str,
        level: SuggestionLevel = SuggestionLevel.WARN,
        priority: SuggestionPriority = SuggestionPriority.P2,
        observation_refs: tuple[str, ...] = ("ev-1",),
        pid_override: str | None = None,
    ) -> PushSuggestionCommand:
        return PushSuggestionCommand(
            suggestion_id=suggestion_id,
            project_id=pid_override or project_id,
            level=level,
            content=content,
            observation_refs=observation_refs,
            priority=priority,
            ts=datetime.now(UTC).isoformat(),
        )

    return _mk
