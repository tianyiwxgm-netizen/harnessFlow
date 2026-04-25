"""Scenario 04 · 5 WP 并发 fixtures · 真实 WBSTopologyManager + L1-09 EventBus.

5 WP 拓扑: wp-1..wp-5 互无依赖 · parallelism_limit=5.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import WorkPackage
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    return "proj-acc04-parallel"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(event_bus_root)


@pytest.fixture
def topo_manager(project_id: str) -> WBSTopologyManager:
    """L1-03 manager · parallelism=5 · 5 WP 全部 READY 同 layer."""
    return WBSTopologyManager(project_id=project_id, parallelism_limit=5)


@pytest.fixture
def make_wp(project_id: str):
    def _mk(wp_id: str, deps: list[str] | None = None) -> WorkPackage:
        return WorkPackage(
            wp_id=wp_id,
            project_id=project_id,
            goal=f"parallel goal · {wp_id}",
            dod_expr_ref=f"dod-{wp_id}",
            deps=deps or [],
            effort_estimate=1.0,
        )

    return _mk


@pytest.fixture
def loaded_topo(topo_manager: WBSTopologyManager, make_wp):
    """5 WP 同一 layer (互无依赖) · parallelism_limit=5."""
    wps = [make_wp(f"wp-{i}") for i in range(1, 6)]
    topo_manager.load_topology(wps, [])
    return topo_manager


@pytest.fixture
def emit_event(real_event_bus: EventBus, project_id: str):
    """工厂 · emit IC-02 status_change 模拟 5 路并发."""

    def _emit(event_type: str, payload: dict, actor: str = "executor") -> str:
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit
