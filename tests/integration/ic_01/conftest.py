"""IC-01 集成测试 fixtures · 真实 StateMachineOrchestrator.

铁律: 真实 import `app.main_loop.state_machine.*` · 不 mock 状态机本体.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest

from app.main_loop.state_machine import (
    State,
    StateMachineOrchestrator,
    TransitionRequest,
)


@pytest.fixture
def project_id() -> str:
    """IC-01 默认 pid · 符合 `pid-{uuid-like}` pattern."""
    return "pid-00000000-0000-0000-0000-0000000ab002"


@pytest.fixture
def transition_id_factory() -> Callable[[], str]:
    def _mk() -> str:
        return f"trans-{uuid.uuid4()}"
    return _mk


@pytest.fixture
def orchestrator(project_id: str) -> StateMachineOrchestrator:
    """干净 orchestrator · 初始 NOT_EXIST."""
    return StateMachineOrchestrator(
        project_id=project_id,
        initial_state="NOT_EXIST",
    )


@pytest.fixture
def make_request(
    project_id: str, transition_id_factory: Callable[[], str],
) -> Callable[..., TransitionRequest]:
    """工厂: 构造 TransitionRequest · 可覆盖任意字段."""

    def _mk(
        *,
        from_state: State = "NOT_EXIST",
        to_state: State = "INITIALIZED",
        reason: str = "IC-01 WP02 集成测试标准 reason ≥ 20 字",
        trigger_tick: str = "tick-00000000-0000-0000-0000-000000000001",
        evidence_refs: tuple[str, ...] = ("ev-wp02-1",),
        ts: str = "2026-04-23T10:00:00.000000Z",
        gate_id: str | None = None,
        transition_id: str | None = None,
        project_id_override: str | None = None,
    ) -> TransitionRequest:
        tid = transition_id or transition_id_factory()
        pid = project_id_override if project_id_override is not None else project_id
        return TransitionRequest(
            transition_id=tid,
            project_id=pid,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            trigger_tick=trigger_tick,
            evidence_refs=evidence_refs,
            ts=ts,
            gate_id=gate_id,
        )

    return _mk


@pytest.fixture
def build_at_state() -> Callable[[str, "State"], StateMachineOrchestrator]:
    """构造一个 orchestrator 并让其处于指定 state · 便于测 12 边."""

    def _mk(pid: str, state: State) -> StateMachineOrchestrator:
        return StateMachineOrchestrator(
            project_id=pid,
            initial_state=state,
        )

    return _mk
