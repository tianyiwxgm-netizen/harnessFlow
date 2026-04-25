"""IC-18 集成 fixtures · 真实 EventBus + AuditQuery 全链.

WP04 任务表 IC-18 = audit_query (L1-10 → L1-09 query_audit_trail).
铁律: 真实 import L1-09 EventBus + AuditQuery · 物理 jsonl 落盘.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.audit import Anchor, AnchorType, AuditQuery, QueryFilter
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


@pytest.fixture
def project_id() -> str:
    return "proj-ic18"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 物理根 · events.jsonl 落在此."""
    return tmp_path / "bus_root"


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(root=event_bus_root)


@pytest.fixture
def audit_query(event_bus_root: Path) -> AuditQuery:
    return AuditQuery(root=event_bus_root)


@pytest.fixture
def seed_events(real_event_bus: EventBus, project_id: str):
    """工厂 · 写若干预置 event 到 bus 物理落盘."""

    def _seed(
        n: int = 5,
        *,
        actor: str = "executor",
        event_type: str = "L1-05:task_done",
        payload_factory=lambda i: {"i": i},
        pid: str | None = None,
    ) -> list[dict]:
        out = []
        for i in range(n):
            evt = Event(
                project_id=pid or project_id,
                type=event_type,
                actor=actor,
                payload=payload_factory(i),
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
            out.append({"i": i, "type": event_type})
        return out

    return _seed


@pytest.fixture
def make_anchor(project_id: str):
    """工厂 · 造合法 Anchor."""

    def _make(
        anchor_id: str | None = None,
        *,
        anchor_type: AnchorType = AnchorType.PROJECT_ID,
        pid: str | None = None,
    ) -> Anchor:
        pid_val = pid or project_id
        return Anchor(
            anchor_type=anchor_type,
            anchor_id=anchor_id or pid_val,
            project_id=pid_val,
        )

    return _make
