"""IC-07 集成 fixtures · 真实 ObserveAccumulator + InMemorySessionStore.

铁律:
    - 真实 import L1-06 observer (ObserveAccumulator 主类)
    - tier_manager=None → 走 in-memory _InMemorySessionStore
    - event_bus 是 mock · 验 emit 调用即可
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.knowledge_base.observer.accumulator import (
    ObserveAccumulator,
    _InMemorySessionStore,
)
from app.knowledge_base.observer.schemas import (
    ApplicableContext,
    KBEntryRequest,
    WriteSessionRequest,
)


@pytest.fixture
def project_id() -> str:
    return "proj-ic07"


@pytest.fixture
def fake_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def repo() -> _InMemorySessionStore:
    return _InMemorySessionStore()


@pytest.fixture
def accumulator(
    fake_event_bus: MagicMock,
    repo: _InMemorySessionStore,
) -> ObserveAccumulator:
    return ObserveAccumulator(
        tier_manager=None,
        event_bus=fake_event_bus,
        repo=repo,
    )


@pytest.fixture
def make_entry():
    """工厂 · 一行造合法 KBEntryRequest."""

    def _make(
        *,
        kind: str = "trap",
        title: str = "OAuth redirect loop",
        content: dict | None = None,
        source_links: list[str] | None = None,
        created_by: str = "L1-04",
    ) -> KBEntryRequest:
        return KBEntryRequest(
            kind=kind,
            title=title,
            content=content or {"trigger": "x", "symptom": "y", "mitigation": "z"},
            applicable_context=ApplicableContext(
                stage=["S3"], task_type=["coding"], tech_stack=["python"],
            ),
            source_links=source_links or ["decision:d1"],
            created_by=created_by,
        )

    return _make


@pytest.fixture
def make_request(project_id: str, make_entry):
    """工厂 · 完整 WriteSessionRequest."""

    def _make(
        *,
        trace_id: str = "trace-ic07-01",
        idempotency_key: str = "",
        entry: KBEntryRequest | None = None,
        pid_override: str | None = None,
    ) -> WriteSessionRequest:
        return WriteSessionRequest(
            project_id=pid_override or project_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            entry=entry if entry is not None else make_entry(),
        )

    return _make
