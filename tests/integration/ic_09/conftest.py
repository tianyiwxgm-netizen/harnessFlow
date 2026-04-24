"""IC-09 集成测试 fixtures · 真实 EventBus / AuditQuery.

WP02 铁律:
    - 真实 L1-09 EventBus (hash-chain + shard + jsonl)
    - 每 TC tmp_path 独立
    - project_id 默认 `proj-wp02` · 缺 pid / 跨 pid 显式改值
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


@pytest.fixture
def project_id() -> str:
    """WP02 默认 project_id."""
    return "proj-wp02"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 EventBus 物理根目录 · 每 TC 独立 tmp_path."""
    return tmp_path / "bus_root"


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · append 写 jsonl · 供 AuditQuery 真查."""
    return EventBus(event_bus_root)


@pytest.fixture
def make_event():
    """构造 Event · 默认字段齐全 · 只需覆盖关键字段."""

    def _mk(
        *,
        project_id: str = "proj-wp02",
        event_type: str = "L1-04:verifier_report_issued",
        actor: str = "verifier",
        payload: dict[str, Any] | None = None,
    ) -> Event:
        return Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            payload=dict(payload or {}),
            timestamp=datetime.now(UTC),
        )

    return _mk
