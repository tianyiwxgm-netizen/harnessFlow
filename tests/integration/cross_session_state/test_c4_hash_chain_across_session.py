"""C4 · arc-history hash 链跨 session 校验 · 2 TC.

events.jsonl 的 hash chain 跨 session 必整 · 重启后第 N+1 条事件的 prev_hash
必须 = 第 N 条的 hash (即使 N 在另一 session 写入).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_hash_chain_intact,
    list_events,
)


class TestC4HashChainAcrossSession:
    """C4 · 跨 session hash-chain 完整 · 2 TC."""

    def test_c4_01_chain_intact_across_two_sessions(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C4.1: Session 1 写 3 条 · Session 2 续写 2 条 · hash-chain 跨 session 完整."""
        # Session 1
        bus1 = EventBus(event_bus_root)
        for i in range(3):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"sess": 1, "i": i},
                timestamp=datetime.now(UTC),
            )
            bus1.append(evt)
        del bus1
        # Session 2 · 重启续写
        bus2 = EventBus(event_bus_root)
        for i in range(2):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"sess": 2, "i": i},
                timestamp=datetime.now(UTC),
            )
            bus2.append(evt)
        # 校 IC-09 hash-chain 跨 session 完整
        chain_len = assert_ic_09_hash_chain_intact(
            event_bus_root, project_id=project_id,
        )
        assert chain_len == 5
        # Session 2 的第 1 条 (seq=4) prev_hash = Session 1 第 3 条的 hash
        events = list_events(event_bus_root, project_id)
        assert events[3]["sequence"] == 4
        assert events[3]["prev_hash"] == events[2]["hash"]
        # Session 2 的第 2 条 (seq=5)
        assert events[4]["sequence"] == 5
        assert events[4]["prev_hash"] == events[3]["hash"]

    def test_c4_02_chain_intact_3_sessions(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C4.2: 3 个 session 各写一条 · hash-chain 跨 3 session 完整."""
        for sess in range(3):
            bus = EventBus(event_bus_root)
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"sess": sess},
                timestamp=datetime.now(UTC),
            )
            bus.append(evt)
            del bus
        # 验完整链
        chain_len = assert_ic_09_hash_chain_intact(
            event_bus_root, project_id=project_id,
        )
        assert chain_len == 3
        events = list_events(event_bus_root, project_id)
        assert [e["sequence"] for e in events] == [1, 2, 3]
        # 每条 prev_hash 都正确链接
        for i in range(1, 3):
            assert events[i]["prev_hash"] == events[i - 1]["hash"]
