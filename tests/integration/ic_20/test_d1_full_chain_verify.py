"""D1 · 完整链 verify · 3 TC.

audit_chain_verify(events.jsonl HASH_CHAIN method) → state=OK · total_items=N · failure_range=None.
"""
from __future__ import annotations

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


class TestD1FullChainVerify:
    """D1 · 完整链 verify · 3 TC."""

    def test_d1_01_empty_chain_verify_ok(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D1.1: 空 events.jsonl(无任何事件) · verify state=OK · total_items=0."""
        # 没写任何事件 · events.jsonl 不存在
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK
        assert report.total_items == 0
        assert report.failure_range is None

    def test_d1_02_5_events_chain_verify_ok(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D1.2: 5 条事件完整链 · verify state=OK · total_items=5."""
        _write_events(real_event_bus, project_id, 5)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK
        assert report.total_items == 5
        assert report.failure_range is None
        # first_good_hash 字段为空(state=OK 时)
        assert report.first_good_hash is None

    def test_d1_03_50_events_chain_verify_ok(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """D1.3: 50 条事件链 · verify 仍 OK · 性能可接受 (≤ 50ms)."""
        _write_events(real_event_bus, project_id, 50)
        events_path = event_bus_root / "projects" / project_id / "events.jsonl"
        report = verify_integrity(events_path, method=IntegrityMethod.HASH_CHAIN)
        assert report.state == IntegrityState.OK
        assert report.total_items == 50
        # scan_duration_ms 性能 SLO
        assert report.scan_duration_ms < 100.0, (
            f"50 条 verify 超 100ms · 实际={report.scan_duration_ms}ms"
        )
