"""D3 · 缺失检测(删一条) · 2 TC.

events.jsonl 中段被删一条 → prev_hash 链断 → verify 报 CORRUPT/PARTIAL.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.crash_safety.integrity_checker import verify_integrity
from app.l1_09.crash_safety.schemas import IntegrityMethod, IntegrityState
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event


def _write_events(bus: EventBus, project_id: str, n: int) -> None:
    for i in range(n):
        evt = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"i": i},
            timestamp=datetime.now(UTC),
        )
        bus.append(evt)


class TestD3MissingDetection:
    """D3 · 链中缺失事件检测 · 2 TC."""

    def test_d3_01_middle_event_removed_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D3.1: 5 条事件中段(index 2)删一条 · verify 报 CORRUPT/PARTIAL.

        prev_hash 链断: index=2 后 · index=3(原)的 prev_hash 不再 = index=2(原)的 hash.
        """
        _write_events(real_event_bus, project_id, 5)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = events_path.read_bytes().splitlines()
        # 删 index=2(第 3 条)
        del lines[2]
        events_path.write_bytes(b"\n".join(lines) + b"\n")
        # verify
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state in (IntegrityState.CORRUPT, IntegrityState.PARTIAL), (
            f"删一条后应非 OK · 实际={report.state}"
        )
        # 头 2 条仍合法 · index=2(原 index=3) 起断
        assert report.failure_range is not None
        # index=2 应是首坏点(原第 4 条 · prev_hash 不匹配)
        assert report.failure_range[0] == 2

    def test_d3_02_first_event_removed_detected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D3.2: 删第 1 条(原 sequence=1) · verify 立即报 CORRUPT(prev_hash 应 = GENESIS).

        删后第一条事件的 prev_hash 还是原第 2 条的(指向第 1 条的 hash) · 不等 GENESIS.
        """
        _write_events(real_event_bus, project_id, 4)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        lines = events_path.read_bytes().splitlines()
        del lines[0]  # 删第 1 条
        events_path.write_bytes(b"\n".join(lines) + b"\n")
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        # 第 1 条 prev_hash != GENESIS · 立即 CORRUPT
        assert report.state == IntegrityState.CORRUPT
        assert report.failure_range is not None
        assert report.failure_range[0] == 0
