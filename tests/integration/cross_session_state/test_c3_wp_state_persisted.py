"""C3 · 未完成 WP 状态保留(WP IN_PROGRESS · 重启 · 仍 IN_PROGRESS) · 3 TC.

通过 IC-09 audit-ledger 持久化 WP 状态变迁事件 · 重启后从 events.jsonl 恢复
WP 当前状态 · 不会被重置.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import list_events


def _emit_wp_state_change(
    bus: EventBus,
    project_id: str,
    wp_id: str,
    new_state: str,
) -> None:
    """模拟 L1-03 wp_state_changed 事件落盘."""
    evt = Event(
        project_id=project_id,
        type="L1-03:wp_scheduled",  # 用合法 type · payload 标 state
        actor="executor",
        payload={
            "wp_id": wp_id,
            "new_state": new_state,
        },
        timestamp=datetime.now(UTC),
    )
    bus.append(evt)


def _replay_latest_wp_states(
    event_bus_root: Path,
    project_id: str,
) -> dict[str, str]:
    """从 events 重放 · 计算每 wp 最后状态."""
    events = list_events(event_bus_root, project_id, type_exact="L1-03:wp_scheduled")
    latest: dict[str, str] = {}
    for e in events:
        wp = e.get("payload", {}).get("wp_id")
        st = e.get("payload", {}).get("new_state")
        if wp and st:
            latest[wp] = st
    return latest


class TestC3WpStatePersisted:
    """C3 · WP 状态跨 session 保留 · 3 TC."""

    def test_c3_01_in_progress_wp_state_kept_after_restart(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C3.1: WP wp-001 → IN_PROGRESS · 销毁 bus · 重启 · 状态仍 IN_PROGRESS."""
        # Session 1
        bus1 = EventBus(event_bus_root)
        _emit_wp_state_change(bus1, project_id, "wp-001", "READY")
        _emit_wp_state_change(bus1, project_id, "wp-001", "IN_PROGRESS")
        del bus1
        # Session 2 · 从 events 重建状态
        states = _replay_latest_wp_states(event_bus_root, project_id)
        assert states["wp-001"] == "IN_PROGRESS"

    def test_c3_02_multiple_wps_each_state_preserved(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C3.2: 多 WP 各自状态 · 重启后逐个恢复."""
        bus = EventBus(event_bus_root)
        _emit_wp_state_change(bus, project_id, "wp-A", "DONE")
        _emit_wp_state_change(bus, project_id, "wp-B", "IN_PROGRESS")
        _emit_wp_state_change(bus, project_id, "wp-C", "READY")
        _emit_wp_state_change(bus, project_id, "wp-D", "FAILED")
        del bus
        # 重启
        states = _replay_latest_wp_states(event_bus_root, project_id)
        assert states == {
            "wp-A": "DONE",
            "wp-B": "IN_PROGRESS",
            "wp-C": "READY",
            "wp-D": "FAILED",
        }

    def test_c3_03_state_transition_chain_preserves_history(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C3.3: WP 多次 state 变迁 · 重启后能 replay 完整历史 · 取最新状态."""
        bus = EventBus(event_bus_root)
        # wp-001 走 4 次跃迁: PLAN → READY → IN_PROGRESS → DONE
        _emit_wp_state_change(bus, project_id, "wp-001", "PLAN")
        _emit_wp_state_change(bus, project_id, "wp-001", "READY")
        _emit_wp_state_change(bus, project_id, "wp-001", "IN_PROGRESS")
        _emit_wp_state_change(bus, project_id, "wp-001", "DONE")
        del bus
        # Session 2
        events = list_events(
            event_bus_root, project_id, type_exact="L1-03:wp_scheduled",
        )
        # 完整历史 4 条都在
        assert len(events) == 4
        states_chain = [e["payload"]["new_state"] for e in events]
        assert states_chain == ["PLAN", "READY", "IN_PROGRESS", "DONE"]
        # 最终状态 DONE
        states = _replay_latest_wp_states(event_bus_root, project_id)
        assert states["wp-001"] == "DONE"
