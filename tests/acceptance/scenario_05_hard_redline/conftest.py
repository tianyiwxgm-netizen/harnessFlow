"""Scenario 05 · 硬红线 fixtures · 真实 L1-07 HaltRequester + L1-01 HaltEnforcer + L1-09 EventBus.

每 TC 独立物理根 (tmp_path) · 自带 EventBusStub (supervisor 内审计) + 真实 EventBus (跨进程 IC-09).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.supervisor_receiver.schemas import HaltSignal
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
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
# 共享 GWT DSL · acceptance 必用
from tests.shared.gwt_helpers import gwt  # noqa: F401


# ============================================================================
# 共用 pid + 物理根
# ============================================================================


@pytest.fixture
def project_id() -> str:
    """scenario 05 默认 pid · HaltRequester 接受 free-form pid 字符串."""
    return "proj-acc05-hard-redline"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 真实 event bus 根目录 · IC-09 落盘 · 跨 session 持久测试用."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · 写 events.jsonl + hash chain · 端到端审计闭环."""
    return EventBus(event_bus_root)


@pytest.fixture
def supervisor_bus() -> EventBusStub:
    """L1-07 内部 stub bus (HaltRequester 用) · 端到端 supervisor → consumer 流之外的兜底."""
    return EventBusStub()


# ============================================================================
# 5 步链:HaltEnforcer (L1-01) + HaltRequester (L1-07) + IC15Consumer (L2-06)
# ============================================================================


@pytest.fixture
def halt_enforcer(project_id: str) -> HaltEnforcer:
    """真实 L2-01 HaltEnforcer · L1-01 halt target · 初始 RUNNING."""
    return HaltEnforcer(project_id=project_id)


@pytest.fixture
def halt_requester(
    project_id: str,
    halt_enforcer: HaltEnforcer,
    supervisor_bus: EventBusStub,
) -> HaltRequester:
    """L1-07 IC-15 producer · 直接挂真 HaltEnforcer 作 target."""
    return HaltRequester(
        session_pid=project_id,
        target=halt_enforcer,
        event_bus=supervisor_bus,
    )


@pytest.fixture
def slow_halt_target() -> MockHardHaltTarget:
    """慢 target · slow_halt_ms=120 · 测 HRL-05 SLO 违反路径."""
    return MockHardHaltTarget(
        initial_state=HardHaltState.RUNNING, slow_halt_ms=120,
    )


class _AsyncEventBusAdapter:
    """L1-09 真实 EventBus 是 sync 接口 · 给 IC15Consumer 包成 async."""

    def __init__(self, real_bus: EventBus, default_pid: str) -> None:
        self._bus = real_bus
        self._default_pid = default_pid

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,  # noqa: A002
        payload: dict,
        evidence_refs: tuple = (),
    ) -> str:
        from app.l1_09.event_bus.schemas import Event

        evt = Event(
            project_id=project_id,
            type=type,
            actor="supervisor",
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        result = self._bus.append(evt)
        return result.event_id


@pytest.fixture
def real_async_bus(real_event_bus: EventBus, project_id: str) -> _AsyncEventBusAdapter:
    """async 包装 L1-09 真实 EventBus · 供 IC15Consumer 端到端测."""
    return _AsyncEventBusAdapter(real_event_bus, project_id)


@pytest.fixture
def ic15_consumer(
    project_id: str,
    halt_enforcer: HaltEnforcer,
    real_async_bus: _AsyncEventBusAdapter,
) -> IC15Consumer:
    """L2-06 IC-15 receiver · 真实 halt_target=HaltEnforcer · 真实 event_bus=L1-09."""
    return IC15Consumer(
        session_pid=project_id,
        halt_target=halt_enforcer,
        event_bus=real_async_bus,
    )


# ============================================================================
# RequestHardHaltCommand 工厂
# ============================================================================


@pytest.fixture
def make_halt_command(project_id: str):
    """工厂 · 给 red_line_id + halt_id → RequestHardHaltCommand."""

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


@pytest.fixture
def make_halt_signal(make_halt_command):
    """工厂 · 把 RequestHardHaltCommand wrap 成 HaltSignal (consumer envelope)."""

    def _mk(
        *,
        red_line_id: str,
        halt_id: str,
        received_at_ms: int = 0,
        **kw,
    ) -> HaltSignal:
        cmd = make_halt_command(red_line_id=red_line_id, halt_id=halt_id, **kw)
        return HaltSignal.from_command(cmd, received_at_ms=received_at_ms)

    return _mk
