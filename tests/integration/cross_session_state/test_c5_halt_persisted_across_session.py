"""C5 · 未授权硬红线 halt 跨 session 持续(halt 状态被持久化) · 2 TC.

L1-09 HaltGuard 写 halt.marker 文件到 _global/ · 跨 session 可见.
重启后新 EventBus 实例检测到 marker · state=HALTED · 拒所有 append.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import (
    BusHalted,
    BusState,
    Event,
)


class TestC5HaltPersistedAcrossSession:
    """C5 · halt 持久化 · 2 TC."""

    def test_c5_01_halt_marker_visible_after_restart(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C5.1: Session 1 mark_halt · 重启 · marker 仍在 · state=HALTED · append 拒.

        IC-15 halt 必须跨 session 持续 · 防自动恢复 (硬红线必须 user authorize).
        """
        # Session 1 · halt
        bus1 = EventBus(event_bus_root)
        bus1.halt_guard.mark_halt(
            reason="test halt c5.01",
            source="test-c5",
            correlation_id="cor-c5-1",
        )
        assert bus1.halt_guard.is_halted() is True
        assert bus1.state == BusState.HALTED
        del bus1
        # Session 2 · marker 仍在
        bus2 = EventBus(event_bus_root)
        assert bus2.halt_guard.is_halted() is True
        assert bus2.state == BusState.HALTED
        # append 应 raise BusHalted
        evt = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={},
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(BusHalted):
            bus2.append(evt)
        # halt info 内容仍可读
        info = bus2.halt_guard.load_halt_info()
        assert info is not None
        assert info["reason"] == "test halt c5.01"
        assert info["source"] == "test-c5"

    def test_c5_02_halt_blocks_3rd_session_append(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C5.2: Session 1 写 OK · halt · Session 2/3 重启都拒 append.

        halt 状态对全局 cross-pid 永久阻塞 · 未 user authorize 永远不解.
        """
        # Session 1 · 写 1 条 + halt
        bus1 = EventBus(event_bus_root)
        evt1 = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"step": "before-halt"},
            timestamp=datetime.now(UTC),
        )
        bus1.append(evt1)
        bus1.halt_guard.mark_halt(
            reason="permanent halt", source="test-c5-02",
        )
        del bus1
        # Session 2 · 拒
        bus2 = EventBus(event_bus_root)
        evt2 = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"step": "after-halt-s2"},
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(BusHalted):
            bus2.append(evt2)
        del bus2
        # Session 3 · 仍拒
        bus3 = EventBus(event_bus_root)
        with pytest.raises(BusHalted):
            bus3.append(evt2)
        # 物理上 events.jsonl 仅 1 条(halt 前那条)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = events_path.read_bytes().splitlines()
        assert len([l for l in lines if l.strip()]) == 1
