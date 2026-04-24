"""L1-06 L2-03 test fixtures · IC-07 kb_write_session."""
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
def mock_project_id() -> str:
    return "hf-proj-l203"


@pytest.fixture
def mock_project_id_other() -> str:
    return "hf-proj-other"


@pytest.fixture
def mock_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_tier_manager() -> MagicMock:
    m = MagicMock()
    m.write_slot_request.return_value = MagicMock(
        schema_valid=True, slot_granted=True, existing_entry_id=None
    )
    return m


@pytest.fixture
def repo() -> _InMemorySessionStore:
    return _InMemorySessionStore()


@pytest.fixture
def sut(
    mock_event_bus: MagicMock,
    repo: _InMemorySessionStore,
) -> ObserveAccumulator:
    """Default SUT without tier_manager (uses in-memory repo)."""
    return ObserveAccumulator(
        tier_manager=None,
        event_bus=mock_event_bus,
        repo=repo,
    )


@pytest.fixture
def sut_with_tier(
    mock_event_bus: MagicMock,
    mock_tier_manager: MagicMock,
    repo: _InMemorySessionStore,
) -> ObserveAccumulator:
    return ObserveAccumulator(
        tier_manager=mock_tier_manager,
        event_bus=mock_event_bus,
        repo=repo,
    )


@pytest.fixture
def make_entry():
    """Factory for a valid KBEntryRequest."""

    _SENTINEL = object()

    def _make(
        *,
        kind: str = "trap",
        title: str = "OAuth redirect loop",
        content=_SENTINEL,
        source_links=_SENTINEL,
        applicable_context: ApplicableContext | None = None,
        project_id: str = "",
        scope: str = "",
        observed_count: int | None = None,
        created_by: str = "L1-04",
    ) -> KBEntryRequest:
        actual_content = (
            {"trigger": "x", "symptom": "y", "mitigation": "z"}
            if content is _SENTINEL
            else content
        )
        actual_links = (
            ["decision:d1"] if source_links is _SENTINEL else list(source_links)
        )
        return KBEntryRequest(
            kind=kind,
            title=title,
            content=actual_content,
            applicable_context=applicable_context
            or ApplicableContext(
                stage=["S3"], task_type=["coding"], tech_stack=["python"]
            ),
            source_links=actual_links,
            created_by=created_by,
            observed_count=observed_count,
            project_id=project_id,
            scope=scope,
        )

    return _make


@pytest.fixture
def make_request(mock_project_id, make_entry):
    """Factory for a full WriteSessionRequest with sensible defaults."""

    def _make(
        *,
        project_id: str | None = None,
        trace_id: str = "t1",
        idempotency_key: str = "",
        entry=None,
    ) -> WriteSessionRequest:
        return WriteSessionRequest(
            project_id=project_id if project_id is not None else mock_project_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
            entry=entry if entry is not None else make_entry(),
        )

    return _make
