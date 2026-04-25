"""Scenario 07 · KB 晋升仪式 fixtures · 真实 PromotionExecutor + L1-09 EventBus.

session 候选 ≥ 5 → user promote/reject → project tier 写入 → IC-08 检索命中.
用 InMemoryTargetStore 做 project/global 落地 · 不依赖外部 KB repo.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_base.observer.schemas import SnapshotEntry, SnapshotManifest
from app.knowledge_base.promoter.promotion_executor import (
    InMemoryTargetStore,
    PromotionExecutor,
)
from app.knowledge_base.promoter.schemas import (
    Approver,
    KBPromoteRequest,
    PromoteTarget,
)
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    return "proj-acc07-kb-promo"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(event_bus_root)


# =============================================================================
# Observer Stub (returns 5+ candidates)
# =============================================================================


class _FakeSourceEntry:
    """Source entry · 模拟 PromotionExecutor 用的 source · 含 project_id 用于 PM-14."""

    def __init__(
        self,
        entry_id: str,
        project_id: str,
        kind: str = "pattern",
        title: str = "obs",
        observed_count: int = 2,
        title_hash: str | None = None,
    ) -> None:
        self.entry_id = entry_id
        self.project_id = project_id
        self.kind = kind
        self.title = title
        self.title_hash = title_hash or f"h-{entry_id}"
        self.content = {"body": f"observation {entry_id}"}
        self.observed_count = observed_count


class FakeObserver:
    """Observer stub · 提供 candidate snapshot · 模拟 ≥5 个 session 观察."""

    def __init__(self, candidates: list[_FakeSourceEntry] | None = None) -> None:
        self.candidates = candidates or []

    def provide_candidate_snapshot(
        self,
        *,
        project_id: str,
        min_observed_count: int = 2,
        kind_filter: list[str] | None = None,
        trace_id: str = "",
    ) -> SnapshotManifest:
        # 注: PromotionExecutor 期望 manifest.entries · 每项是 source-style entry
        # 不是 SnapshotEntry · 所以我们直接返回带 entries 的 manifest-like 对象
        results = [
            c for c in self.candidates
            if c.project_id == project_id and c.observed_count >= min_observed_count
        ]
        if kind_filter:
            results = [c for c in results if c.kind in kind_filter]

        # build a duck-typed manifest with .entries · _lookup_source 直接迭代 entries
        class _Manifest:
            def __init__(self, entries: list[_FakeSourceEntry]) -> None:
                self.entries = entries
                self.error_code = None
                self.total_entries = len(entries)

        return _Manifest(results)


@pytest.fixture
def fake_observer():
    pid = "proj-acc07-kb-promo"
    candidates = [
        _FakeSourceEntry(
            entry_id=f"sess-{i:03d}",
            project_id=pid,
            kind="pattern",
            title=f"observation-{i}",
            title_hash=f"hash-{i}",
            observed_count=2 + (i % 3),  # 2..4
        )
        for i in range(1, 6)
    ]
    return FakeObserver(candidates)


@pytest.fixture
def target_store():
    return InMemoryTargetStore()


@pytest.fixture
def promotion_executor(fake_observer, target_store):
    """L1-06 PromotionExecutor · in-memory target store · 默认 approval gate."""
    return PromotionExecutor(
        observer=fake_observer,
        tier_manager=None,
        event_bus=None,
        target_store=target_store,
    )


@pytest.fixture
def emit_audit(real_event_bus: EventBus, project_id: str):
    """工厂 · 模拟 IC-07 / IC-08 audit emit."""

    def _emit(event_type: str, payload: dict, actor: str = "main_loop") -> str:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit
