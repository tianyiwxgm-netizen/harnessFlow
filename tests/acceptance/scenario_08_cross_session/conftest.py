"""scenario_08 · cross-session 状态恢复 · 共享 fixtures.

**真实组件**:
    - L1-09 EventBus(append + halt_guard + hash chain)
    - L1-09 SnapshotJob(checkpoint snapshot)
    - L1-09 RecoveryAttempt(Tier 1-4 恢复策略)

**模拟崩溃路径**:
    1. 跑一段(events 落盘)
    2. SnapshotJob.take_snapshot(pid) 落 checkpoint
    3. 继续跑(events 落盘 · 超过 checkpoint 的 last_seq)
    4. 模拟"崩溃" = 销毁 EventBus / SnapshotJob 内存对象
    5. 用新 RecoveryAttempt + 同物理 root 跑 recover_from_checkpoint
    6. 验证 recovered_state · 续运行可正常 append

**PID**: pid=`proj-acceptance-08`
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.checkpoint import RecoveryAttempt, SnapshotJob
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    return "proj-acceptance-08"


@pytest.fixture
def bus_root(tmp_path: Path) -> Path:
    """L1-09 物理根 · 跨 session 持久("崩溃"后此 root 仍可读)."""
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def event_bus_root(bus_root: Path) -> Path:
    """alias for shared assertion helpers."""
    return bus_root


@pytest.fixture
def event_bus_v1(bus_root: Path) -> EventBus:
    """第一次 session 的 EventBus(用完后 del 模拟崩溃)."""
    return EventBus(bus_root)


@pytest.fixture
def snapshot_job_v1(event_bus_v1: EventBus, bus_root: Path) -> SnapshotJob:
    return SnapshotJob(bus_root, event_bus=event_bus_v1)


# ============================================================================
# session-bridge helper · 模拟"崩溃 + 重启" · 把同一 bus_root 重新打开为 v2
# ============================================================================


@pytest.fixture
def restart_session(bus_root: Path):
    """工厂 · 给一个 EventBus 实例(模拟"重启后" recover 用)."""
    def _restart() -> EventBus:
        return EventBus(bus_root)
    return _restart


@pytest.fixture
def recovery_v2(bus_root: Path):
    """重启后用的新 RecoveryAttempt · 关键约束: 接同 bus_root + 接重启的 EventBus."""
    def _make(bus: EventBus) -> RecoveryAttempt:
        return RecoveryAttempt(bus_root, event_bus=bus)
    return _make


# ============================================================================
# pre-crash 场景构造器: 跑 N events + 落 checkpoint(可被 v2 recover)
# ============================================================================


def append_n_events(
    bus: EventBus,
    project_id: str,
    n: int,
    *,
    type_prefix: str = "L1-03",
    actor: str = "planner",
    payload_extra: dict | None = None,
) -> int:
    """append n 个 typed events · 返实际 append 数."""
    base_extra = payload_extra or {}
    for i in range(n):
        evt = Event(
            project_id=project_id,
            type=f"{type_prefix}:test_event",
            actor=actor,
            timestamp=datetime.now(UTC),
            payload={"i": i, **base_extra},
        )
        bus.append(evt)
    return n


@pytest.fixture
def append_events(event_bus_v1: EventBus, project_id: str):
    """快捷 helper · 在 v1 session 内追加 n 个事件."""
    def _append(n: int, *, type_prefix: str = "L1-03", payload_extra: dict | None = None) -> int:
        return append_n_events(
            event_bus_v1,
            project_id,
            n,
            type_prefix=type_prefix,
            payload_extra=payload_extra,
        )
    return _append
