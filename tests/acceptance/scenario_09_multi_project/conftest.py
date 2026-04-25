"""Scenario 09 · multi-project fixtures · 3 pid 独立 manager + 共享 EventBus 物理根.

L1-09 EventBus 用 PM-14 分片 · 同 1 物理根下 3 pid 自然隔离.
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


# 3 pid 常量 · L1-09 严格 ^[a-z0-9_-]{1,40}$
PID_A = "proj-acc09-pid-a"
PID_B = "proj-acc09-pid-b"
PID_C = "proj-acc09-pid-c"


@pytest.fixture
def pid_a() -> str:
    return PID_A


@pytest.fixture
def pid_b() -> str:
    return PID_B


@pytest.fixture
def pid_c() -> str:
    return PID_C


@pytest.fixture
def all_pids() -> tuple[str, str, str]:
    return (PID_A, PID_B, PID_C)


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    """单一物理 root · 3 pid 共享 · 但分片自然隔离."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    """真实 L1-09 · 3 pid 共享同 bus · 分片落 projects/<pid>/events.jsonl."""
    return EventBus(event_bus_root)


@pytest.fixture
def emit_for(real_event_bus: EventBus):
    """工厂 · 给指定 pid emit IC-09 audit."""

    def _emit(pid: str, event_type: str, payload: dict, actor: str = "main_loop") -> str:
        evt = Event(
            project_id=pid,
            type=event_type,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload=payload,
        )
        return real_event_bus.append(evt).event_id

    return _emit


@pytest.fixture
def topo_factory():
    """工厂 · 单独构造每 pid 的 WBSTopologyManager."""

    def _mk(pid: str, parallelism: int = 2) -> WBSTopologyManager:
        return WBSTopologyManager(project_id=pid, parallelism_limit=parallelism)

    return _mk


@pytest.fixture
def make_wp_for():
    """工厂 · 按 pid 造 WP."""

    def _mk(pid: str, wp_id: str, *, deps: list[str] | None = None) -> WorkPackage:
        return WorkPackage(
            wp_id=wp_id,
            project_id=pid,
            goal=f"goal · {wp_id}",
            dod_expr_ref=f"dod-{wp_id}",
            deps=deps or [],
            effort_estimate=1.0,
        )

    return _mk
