"""L1-06 L2-04 · fixtures for PromotionExecutor."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import (
    Approver,
    BatchScope,
    KBPromoteRequest,
    PromoteTarget,
)


@pytest.fixture
def mock_project_id() -> str:
    return "hf-proj-l204"


@pytest.fixture
def target_store() -> InMemoryTargetStore:
    return InMemoryTargetStore()


@pytest.fixture
def mock_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def make_source_entry():
    """Factory for a minimal source entry usable by PromotionExecutor."""

    def _make(
        *,
        entry_id: str = "kbe-s-1",
        project_id: str = "hf-proj-l204",
        kind: str = "pattern",
        title: str = "stored entry",
        title_hash: str = "00" * 16,
        content: dict | None = None,
        observed_count: int = 1,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            entry_id=entry_id,
            project_id=project_id,
            kind=kind,
            title=title,
            title_hash=title_hash,
            content=content or {"x": 1},
            observed_count=observed_count,
        )

    return _make


@pytest.fixture
def mock_observer(make_source_entry) -> MagicMock:
    """An observer that provides a configurable candidate snapshot."""
    m = MagicMock()
    m._entries_by_project = {}

    def _snapshot(*, project_id, min_observed_count=2, kind_filter=None, trace_id=""):
        entries = m._entries_by_project.get(project_id, [])
        filtered = [
            e for e in entries
            if e.observed_count >= min_observed_count
            and (not kind_filter or e.kind in kind_filter)
        ]
        return SimpleNamespace(
            project_id=project_id,
            total_entries=len(filtered),
            entries=filtered,
            error_code=None,
            kind_filter=list(kind_filter or []),
            snapshot_id=f"snap-{project_id}",
        )

    m.provide_candidate_snapshot.side_effect = _snapshot
    return m


@pytest.fixture
def sut(
    mock_observer: MagicMock,
    mock_event_bus: MagicMock,
    target_store: InMemoryTargetStore,
) -> PromotionExecutor:
    return PromotionExecutor(
        observer=mock_observer,
        tier_manager=None,
        event_bus=mock_event_bus,
        target_store=target_store,
    )


@pytest.fixture
def make_promote_request(mock_project_id):
    """Factory for a KBPromoteRequest (single/batch)."""

    def _make(
        *,
        mode: str = "single",
        trigger: str = "user_manual",
        request_id: str = "req-1",
        target: PromoteTarget | None = None,
        batch_scope: BatchScope | None = None,
        project_id: str | None = None,
    ) -> KBPromoteRequest:
        return KBPromoteRequest(
            project_id=project_id if project_id is not None else mock_project_id,
            mode=mode,
            trigger=trigger,
            request_id=request_id,
            target=target,
            batch_scope=batch_scope,
        )

    return _make


__all__ = [
    "Approver",
    "BatchScope",
    "PromoteTarget",
]
