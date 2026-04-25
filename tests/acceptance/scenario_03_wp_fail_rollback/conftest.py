"""Scenario 03 · WP-fail rollback fixtures · 真实 IC14Consumer · L2-07 4 级回退.

L2-07 IC14Consumer 端到端: classify → map → execute → IC-09 audit.
state_transition 用 spy 记录 · event_bus 用 L1-09 真实落盘.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.quality_loop.rollback_router.ic_14_consumer import IC14Consumer
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)
from tests.shared.gwt_helpers import gwt  # noqa: F401


# =============================================================================
# pid + 物理根
# =============================================================================


@pytest.fixture
def project_id() -> str:
    """Scenario 03 默认 pid · L1-09 严格 ^[a-z0-9_-]{1,40}$."""
    return "proj-acc03-rollback"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 真实 event bus 根目录."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """L1-09 真实 EventBus · IC-09 audit 真落盘."""
    return EventBus(event_bus_root)


# =============================================================================
# state_transition Spy + EventBus async adapter (与 scenario_05 复用同模式)
# =============================================================================


class StateTransitionSpy:
    """L1-02 IC-01 spy · 录调用 · 默认 noop · 可注入 raise."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raise_on_call: bool = False
        self.raise_exc: Exception = RuntimeError("test failure")

    async def state_transition(self, **kw: Any) -> dict[str, Any]:
        self.calls.append(kw)
        if self.raise_on_call:
            raise self.raise_exc
        return {"ok": True, "wp_id": kw.get("wp_id")}


class _AsyncEventBusAdapter:
    """sync L1-09 EventBus → async append_event 包装器."""

    def __init__(self, real_bus: EventBus) -> None:
        self._bus = real_bus

    async def append_event(
        self,
        *,
        project_id: str,
        type: str,  # noqa: A002
        payload: dict,
        evidence_refs: tuple = (),
    ) -> str:
        merged = dict(payload)
        if evidence_refs:
            merged["evidence_refs"] = list(evidence_refs)
        evt = Event(
            project_id=project_id,
            type=type,
            actor="executor",
            timestamp=datetime.now(UTC),
            payload=merged,
        )
        return self._bus.append(evt).event_id


@pytest.fixture
def state_spy() -> StateTransitionSpy:
    return StateTransitionSpy()


@pytest.fixture
def real_async_bus(real_event_bus: EventBus) -> _AsyncEventBusAdapter:
    return _AsyncEventBusAdapter(real_event_bus)


@pytest.fixture
def ic14_consumer(
    project_id: str,
    state_spy: StateTransitionSpy,
    real_async_bus: _AsyncEventBusAdapter,
) -> IC14Consumer:
    """L2-07 IC14Consumer 端到端 · pid 一致 · 真实 audit."""
    return IC14Consumer(
        session_pid=project_id,
        state_transition=state_spy,
        event_bus=real_async_bus,
    )


# =============================================================================
# PushRollbackRouteCommand 工厂
# =============================================================================


@pytest.fixture
def emit_audit_factory(real_event_bus: EventBus, project_id: str):
    """工厂 · 直接 append L1-09 用于模拟 verifier / L1-04 自身 emit."""

    def _emit(event_type: str, payload: dict, actor: str = "verifier") -> str:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit


@pytest.fixture
def make_route_cmd(project_id: str):
    """工厂 · verdict + target_stage + level_count → PushRollbackRouteCommand."""

    def _mk(
        *,
        route_id: str,
        wp_id: str,
        verdict: FailVerdict,
        target_stage: TargetStage,
        level_count: int = 1,
        verifier_report_id: str | None = None,
    ) -> PushRollbackRouteCommand:
        return PushRollbackRouteCommand(
            route_id=route_id,
            project_id=project_id,
            wp_id=wp_id,
            verdict=verdict,
            target_stage=target_stage,
            level_count=level_count,
            evidence=RouteEvidence(
                verifier_report_id=verifier_report_id or f"vr-{route_id}",
            ),
            ts=datetime.now(UTC).isoformat(),
        )

    return _mk
