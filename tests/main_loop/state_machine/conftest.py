"""L2-03 状态机编排器 · 公共 fixtures。"""
from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timezone
from typing import Callable, Iterable

import pytest

from app.main_loop.state_machine import (
    IdempotencyTracker,
    State,
    StateMachineOrchestrator,
    TransitionRequest,
)


@pytest.fixture
def project_id() -> str:
    """稳定 pid · 符合 `pid-{uuid}` 格式。"""
    return "pid-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def clock_iter() -> Iterable[datetime]:
    """单调递增时钟 · 每次调用返回下一个 UTC 时间 (+1s)。"""
    base = datetime(2026, 4, 23, 0, 0, 0, tzinfo=timezone.utc)
    counter = itertools.count()

    def _tick() -> datetime:
        return base.replace(second=next(counter) % 60)

    return _tick  # type: ignore[return-value]


@pytest.fixture
def transition_id_factory() -> Callable[[], str]:
    """每次生成唯一 trans-{uuid}。"""
    def _make() -> str:
        return f"trans-{uuid.uuid4()}"
    return _make


@pytest.fixture
def make_request(
    project_id: str, transition_id_factory: Callable[[], str]
) -> Callable[..., TransitionRequest]:
    """DSL · 快速拼 TransitionRequest · 可覆盖任意字段。"""

    def _make(
        *,
        from_state: State = "NOT_EXIST",
        to_state: State = "INITIALIZED",
        reason: str = "bootstrap kickoff reason for stage transition >=20",
        trigger_tick: str = "tick-00000000-0000-0000-0000-000000000001",
        evidence_refs: tuple[str, ...] = ("ev-1",),
        ts: str = "2026-04-23T00:00:00.000Z",
        gate_id: str | None = None,
        transition_id: str | None = None,
        project_id_override: str | None = None,
    ) -> TransitionRequest:
        return TransitionRequest(
            transition_id=transition_id or transition_id_factory(),
            project_id=project_id_override or project_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            trigger_tick=trigger_tick,
            evidence_refs=evidence_refs,
            ts=ts,
            gate_id=gate_id,
        )

    return _make


@pytest.fixture
def orchestrator(
    project_id: str, clock_iter
) -> StateMachineOrchestrator:
    """干净 orchestrator · 初始 NOT_EXIST · 稳定时钟。"""
    return StateMachineOrchestrator(
        project_id=project_id,
        clock=clock_iter,
        initial_state="NOT_EXIST",
    )


@pytest.fixture
def tracker() -> IdempotencyTracker:
    return IdempotencyTracker()
