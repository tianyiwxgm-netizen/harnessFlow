"""IC-02 集成 fixtures · 真实 L1-03 WBSTopologyManager + L1-09 EventBus 适配.

铁律:
- 真实 import `app.l1_03.topology.*` · 不 mock topology 本体
- 真实 L1-09 EventBus(IC-09 唯一写入口) · 落盘 events.jsonl
- L1-03 内部 emit 走 EventBusStub adapter(L1-03 expects `append(type, content, pid)`)
  + 桥接到 real_event_bus 的 IC-09 schema(`append(Event)`)
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge, WorkPackage
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


# IC-02 本地定义 PM-14 fixture(避 tests/shared/conftest.py 不自动加载)


@pytest.fixture
def project_id() -> str:
    """IC-02 默认 pid · PM-14 分片根字段."""
    return "proj-ic02"


@pytest.fixture
def other_project_id() -> str:
    """跨 pid 隔离测试用."""
    return "proj-ic02-other"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """L1-09 EventBus 物理根 · 每 TC 独立 tmp_path."""
    return tmp_path / "bus_root"


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 EventBus · append 写 jsonl · 落 IC-09 单写入口."""
    return EventBus(event_bus_root)


class L103ToL109Bridge:
    """适配 L1-03 期望的 `append(event_type, content, project_id)` 接口
    到 L1-09 EventBus 的 `append(Event)` IC-09 schema.

    L1-03 内部 emit 都走本桥接 → 落到真实 events.jsonl(IC-09 单写入口).
    """

    def __init__(self, real_bus: EventBus) -> None:
        self._real = real_bus

    def append(
        self,
        event_type: str,
        content: dict[str, Any] | None = None,
        project_id: str = "",
    ) -> dict[str, Any]:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor="executor",  # L1-03 默认 actor
            payload=dict(content or {}),
            timestamp=datetime.now(UTC),
        )
        result = self._real.append(evt)
        return {
            "event_id": result.event_id,
            "sequence": result.sequence,
            "hash": result.hash,
            "prev_hash": result.prev_hash,
            "persisted": result.persisted,
        }


@pytest.fixture
def bus_bridge(real_event_bus: EventBus) -> L103ToL109Bridge:
    """L1-03 → L1-09 桥接 · 给 WBSTopologyManager 注入."""
    return L103ToL109Bridge(real_event_bus)


@pytest.fixture
def make_wp(project_id: str):
    """工厂: 构造 WorkPackage · 默认 4 件套齐全 · state=READY."""

    def _make(
        wp_id: str,
        *,
        deps: list[str] | None = None,
        state: State = State.READY,
        proj: str | None = None,
    ) -> WorkPackage:
        return WorkPackage(
            wp_id=wp_id,
            project_id=proj if proj is not None else project_id,
            goal="ic-02 集成测试 wp",
            dod_expr_ref="dod-default",
            deps=list(deps or []),
            effort_estimate=1.0,
            recommended_skills=[],
            state=state,
        )

    return _make


@pytest.fixture
def manager(
    project_id: str, bus_bridge: L103ToL109Bridge,
) -> WBSTopologyManager:
    """干净 WBSTopologyManager · bus 桥接到真实 L1-09."""
    return WBSTopologyManager(
        project_id=project_id, event_bus=bus_bridge,
    )


@pytest.fixture
def linear_wbs(make_wp):
    """3-WP 线性链 wp-001 → wp-002 → wp-003 · 全 READY · IC-02 用."""
    wps = [
        make_wp("wp-001"),
        make_wp("wp-002", deps=["wp-001"]),
        make_wp("wp-003", deps=["wp-002"]),
    ]
    edges = [
        DAGEdge(from_wp_id="wp-001", to_wp_id="wp-002"),
        DAGEdge(from_wp_id="wp-002", to_wp_id="wp-003"),
    ]
    return wps, edges
