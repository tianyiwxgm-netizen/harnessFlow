"""failure_propagation 测试 fixtures · 真实 L1-09 EventBus + supervisor 真实 halt_requester.

继承 tests/shared 的 fixture · 本 conftest 仅补:
    - halt_target: MockHardHaltTarget(可注入 slow_halt_ms)
    - halt_requester_factory: 构造 HaltRequester
    - sup_event_bus: supervisor 内 stub bus (vs L1-09 真实 bus)
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

# Re-export shared fixtures
from tests.shared.conftest import (  # noqa: F401
    audit_sink,
    callback_waiter,
    ckpt_root,
    delegate_stub,
    event_bus_root,
    fake_kb_repo,
    fake_llm,
    fake_reranker,
    fake_scope_checker,
    fake_skill_invoker,
    fake_tool_client,
    kb_root,
    lock_root,
    no_sleep,
    other_project_id,
    project_id,
    projects_root,
    real_event_bus,
    state_spy,
    tmp_root,
)

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
def halt_target() -> MockHardHaltTarget:
    """L1-01 halt 接收者 · 可注入 slow_halt_ms."""
    return MockHardHaltTarget(initial_state=HardHaltState.RUNNING)


@pytest.fixture
def sup_event_bus() -> EventBusStub:
    """supervisor 内置 IC-09/IC-11 双接口 stub bus."""
    return EventBusStub()


@pytest.fixture
def halt_requester(
    project_id: str,
    halt_target: MockHardHaltTarget,
    sup_event_bus: EventBusStub,
) -> HaltRequester:
    """IC-15 HaltRequester · session_pid 锁定为 project_id."""
    return HaltRequester(
        session_pid=project_id,
        target=halt_target,
        event_bus=sup_event_bus,
    )


@pytest.fixture
def make_halt_command():
    """构造合法 IC-15 RequestHardHaltCommand · 默认 confirmation_count=2."""

    def _mk(
        *,
        project_id: str,
        red_line_id: str = "HRL-01",
        halt_id: str = "halt-001",
        observation_refs: tuple[str, ...] = ("obs-1", "obs-2"),
        confirmation_count: int = 2,
        ts: str | None = None,
    ) -> RequestHardHaltCommand:
        return RequestHardHaltCommand(
            halt_id=halt_id,
            project_id=project_id,
            red_line_id=red_line_id,
            evidence=HardHaltEvidence(
                observation_refs=observation_refs,
                tool_use_id="tool-test",
                confirmation_count=confirmation_count,
            ),
            require_user_authorization=True,
            ts=ts or datetime.now(UTC).isoformat(),
        )

    return _mk
