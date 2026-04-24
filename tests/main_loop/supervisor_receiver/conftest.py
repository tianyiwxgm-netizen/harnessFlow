"""main-2 WP06 · L1-01 L2-06 supervisor_receiver · 共享 fixtures。

Dev-ζ 生产端（merged 到 main）+ main-1 L1-04 L2-07 IC14Consumer 组合。
monotonic 时钟（frozen）· mock event bus · Dev-ζ pusher + 真实 rollback_router。
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from app.main_loop.supervisor_receiver.schemas import (
    AdviceLevel,
    HaltSignal,
    RollbackInbox,
    SuggestionInbox,
)
from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
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


@pytest.fixture
def pid() -> str:
    return f"pid-{uuid.uuid4()}"


@pytest.fixture
def frozen_clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def event_bus() -> EventBusStub:
    return EventBusStub()


# ---------- factories · IC-13 / IC-14 / IC-15 payload ---------- #


@pytest.fixture
def make_suggestion_cmd() -> Callable[..., PushSuggestionCommand]:
    """构造 Dev-ζ `PushSuggestionCommand` · 覆盖字段可通过 overrides。"""

    def _factory(**overrides: Any) -> PushSuggestionCommand:
        base: dict[str, Any] = {
            "suggestion_id": f"sugg-{uuid.uuid4().hex[:12]}",
            "project_id": "pid-default",
            "level": SuggestionLevel.WARN,
            "content": "Supervisor 建议内容 · 默认 ≥10 字",
            "observation_refs": ("evt-default-1",),
            "priority": SuggestionPriority.P2,
            "require_ack_tick_delta": 1,
            "ts": "2026-04-23T00:00:00Z",
        }
        base.update(overrides)
        # 若 overrides 传 str level · 自动转 enum
        if isinstance(base["level"], str):
            base["level"] = SuggestionLevel(base["level"])
        return PushSuggestionCommand(**base)

    return _factory


@pytest.fixture
def make_rollback_cmd() -> Callable[..., PushRollbackRouteCommand]:
    def _factory(**overrides: Any) -> PushRollbackRouteCommand:
        base: dict[str, Any] = {
            "route_id": f"route-{uuid.uuid4().hex[:12]}",
            "project_id": "pid-default",
            "wp_id": "wp-001",
            "verdict": FailVerdict.FAIL_L2,
            "target_stage": TargetStage.S4,
            "level_count": 1,
            "evidence": RouteEvidence(verifier_report_id="vr-001"),
            "ts": "2026-04-23T00:00:00Z",
        }
        base.update(overrides)
        return PushRollbackRouteCommand(**base)

    return _factory


@pytest.fixture
def make_halt_cmd() -> Callable[..., RequestHardHaltCommand]:
    def _factory(**overrides: Any) -> RequestHardHaltCommand:
        base: dict[str, Any] = {
            "halt_id": f"halt-{uuid.uuid4().hex[:12]}",
            "project_id": "pid-default",
            "red_line_id": "redline-rm-rf-system",
            "evidence": HardHaltEvidence(
                observation_refs=("evt-danger-1", "evt-danger-2"),
                confirmation_count=2,
            ),
            "require_user_authorization": True,
            "ts": "2026-04-23T00:00:00Z",
        }
        base.update(overrides)
        return RequestHardHaltCommand(**base)

    return _factory


# ---------- factories · receiver-side envelope ---------- #


@pytest.fixture
def make_suggestion_inbox(
    make_suggestion_cmd: Callable[..., PushSuggestionCommand],
) -> Callable[..., SuggestionInbox]:
    def _factory(**overrides: Any) -> SuggestionInbox:
        received_at_ms = overrides.pop("received_at_ms", 0)
        cmd = make_suggestion_cmd(**overrides)
        return SuggestionInbox.from_command(cmd, received_at_ms=received_at_ms)

    return _factory


@pytest.fixture
def make_rollback_inbox(
    make_rollback_cmd: Callable[..., PushRollbackRouteCommand],
) -> Callable[..., RollbackInbox]:
    def _factory(**overrides: Any) -> RollbackInbox:
        received_at_ms = overrides.pop("received_at_ms", 0)
        cmd = make_rollback_cmd(**overrides)
        return RollbackInbox.from_command(cmd, received_at_ms=received_at_ms)

    return _factory


@pytest.fixture
def make_halt_signal(
    make_halt_cmd: Callable[..., RequestHardHaltCommand],
) -> Callable[..., HaltSignal]:
    def _factory(**overrides: Any) -> HaltSignal:
        received_at_ms = overrides.pop("received_at_ms", 0)
        cmd = make_halt_cmd(**overrides)
        return HaltSignal.from_command(cmd, received_at_ms=received_at_ms)

    return _factory
