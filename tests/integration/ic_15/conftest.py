"""IC-15 集成 fixtures · 真实 HaltRequester + MockHardHaltTarget.

铁律:
- 真实 import `app.supervisor.event_sender.halt_requester`
- 真实 import `app.main_loop.tick_scheduler.halt_enforcer.HaltEnforcer` (作为 prod target)
- 100ms SLO 硬约束 · pytest-benchmark 强校验
- IC-09 审计 stub(supervisor 自带 EventBusStub)
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    HardHaltState,
    RequestHardHaltCommand,
)


@pytest.fixture
def project_id() -> str:
    return "proj-ic15"


@pytest.fixture
def other_project_id() -> str:
    return "proj-ic15-other"


@pytest.fixture
def supervisor_bus() -> EventBusStub:
    return EventBusStub()


@pytest.fixture
def halt_target() -> MockHardHaltTarget:
    """快速 halt target · 默认 RUNNING · halt 后 → HALTED."""
    return MockHardHaltTarget(initial_state=HardHaltState.RUNNING)


@pytest.fixture
def halt_target_slow() -> MockHardHaltTarget:
    """慢 target · slow_halt_ms=120 · 触发 SLO 违反路径(HRL-05 release blocker)."""
    return MockHardHaltTarget(
        initial_state=HardHaltState.RUNNING, slow_halt_ms=120,
    )


@pytest.fixture
def halt_requester(
    project_id: str,
    halt_target: MockHardHaltTarget,
    supervisor_bus: EventBusStub,
) -> HaltRequester:
    return HaltRequester(
        session_pid=project_id,
        target=halt_target,
        event_bus=supervisor_bus,
    )


@pytest.fixture
def make_halt_command(project_id: str):
    """工厂 · 给 red_line_id → RequestHardHaltCommand · 默认 evidence 合规."""

    def _mk(
        *,
        red_line_id: str,
        halt_id: str,
        observation_refs: tuple[str, ...] = ("ev-obs-1", "ev-obs-2"),
        confirmation_count: int = 2,
        pid_override: str | None = None,
    ) -> RequestHardHaltCommand:
        return RequestHardHaltCommand(
            halt_id=halt_id,
            project_id=pid_override or project_id,
            red_line_id=red_line_id,
            evidence=HardHaltEvidence(
                observation_refs=observation_refs,
                confirmation_count=confirmation_count,
            ),
            require_user_authorization=True,
            ts=datetime.now(UTC).isoformat(),
        )

    return _mk
