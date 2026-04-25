"""IC-08 集成 fixtures · 真实 PromotionExecutor + InMemoryTargetStore + 假 observer.

铁律:
    - 真实 import L1-06 promoter (PromotionExecutor)
    - target_store 是真 InMemoryTargetStore (不是 mock)
    - observer 是配置化 mock · 提供 candidate snapshot
"""
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
def project_id() -> str:
    return "proj-ic08"


@pytest.fixture
def target_store() -> InMemoryTargetStore:
    return InMemoryTargetStore()


@pytest.fixture
def fake_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def make_source_entry(project_id: str):
    """工厂 · 造源 entry (in observer manifest)."""

    def _make(
        *,
        entry_id: str = "kbe-src-1",
        kind: str = "pattern",
        title: str = "default",
        title_hash: str = "ab" * 16,
        content: dict | None = None,
        observed_count: int = 2,  # 默认满足 PROJECT_THRESHOLD
        pid: str | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            entry_id=entry_id,
            project_id=pid if pid is not None else project_id,
            kind=kind,
            title=title,
            title_hash=title_hash,
            content=content or {"x": 1},
            observed_count=observed_count,
        )

    return _make


@pytest.fixture
def mock_observer(make_source_entry) -> MagicMock:
    """observer · provide_candidate_snapshot 返预置 entries."""
    m = MagicMock()
    m._entries_by_project: dict[str, list] = {}

    def _snapshot(
        *, project_id, min_observed_count=2, kind_filter=None, trace_id="",
    ):
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
def executor(
    mock_observer: MagicMock,
    fake_event_bus: MagicMock,
    target_store: InMemoryTargetStore,
) -> PromotionExecutor:
    return PromotionExecutor(
        observer=mock_observer,
        tier_manager=None,
        event_bus=fake_event_bus,
        target_store=target_store,
    )


@pytest.fixture
def make_request(project_id: str):
    """工厂 · 造 KBPromoteRequest (single 默认)."""

    def _make(
        *,
        mode: str = "single",
        trigger: str = "user_manual",
        request_id: str = "req-ic08",
        target: PromoteTarget | None = None,
        batch_scope: BatchScope | None = None,
        pid_override: str | None = None,
    ) -> KBPromoteRequest:
        return KBPromoteRequest(
            project_id=pid_override if pid_override is not None else project_id,
            mode=mode,
            trigger=trigger,
            request_id=request_id,
            target=target,
            batch_scope=batch_scope,
        )

    return _make


@pytest.fixture
def make_target():
    """工厂 · PromoteTarget."""

    def _make(
        *,
        entry_id: str = "kbe-src-1",
        from_scope: str = "session",
        to_scope: str = "project",
        reason: str = "auto_threshold",
        approver_user_id: str | None = None,
    ) -> PromoteTarget:
        approver = (
            Approver(user_id=approver_user_id) if approver_user_id else None
        )
        return PromoteTarget(
            entry_id=entry_id,
            from_scope=from_scope,
            to_scope=to_scope,
            reason=reason,
            approver=approver,
        )

    return _make
