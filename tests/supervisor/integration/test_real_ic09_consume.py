"""WP-ζ-07 集成 TC · 真实 L1-09 event_bus 消费验证。

使用 Dev-α 已 merged 的 app.l1_09.event_bus.EventBus · 验证 supervisor 事件能落盘
+ 被 read_range 拉出来。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus import EventBus
from app.supervisor.common.real_bus_adapter import L109EventBusAdapter
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)


@pytest.fixture
def real_bus_root(tmp_path: Path) -> Path:
    return tmp_path / "l1_09_root"


@pytest.fixture
def real_bus(real_bus_root: Path) -> EventBus:
    return EventBus(root=real_bus_root)


@pytest.fixture
def adapter(real_bus: EventBus) -> L109EventBusAdapter:
    return L109EventBusAdapter(real_bus)


class TestRealL109Append:
    @pytest.mark.asyncio
    async def test_adapter_append_event_writes_real_bus(
        self, adapter: L109EventBusAdapter
    ) -> None:
        ev_id = await adapter.append_event(
            project_id="proj-real01",
            type="L1-07:snapshot_captured",
            payload={"snapshot_id": "snap-1", "degradation_level": "FULL"},
            evidence_refs=("ev-a",),
        )
        assert ev_id

    @pytest.mark.asyncio
    async def test_read_range_pulls_written_events(
        self,
        adapter: L109EventBusAdapter,
        real_bus: EventBus,
    ) -> None:
        pid = "proj-real02"
        await adapter.append_event(
            project_id=pid,
            type="L1-07:suggestion_pushed",
            payload={"suggestion_id": "sugg-1", "level": "WARN", "queue_len": 1},
        )
        await adapter.append_event(
            project_id=pid,
            type="L1-07:redline_scan_completed",
            payload={"scan_id": "scan-1", "hit_count": 0},
        )
        # 通过 adapter.read_event_stream 拉
        evs = await adapter.read_event_stream(pid)
        assert len(evs) == 2
        types = {e.type for e in evs}
        assert "L1-07:suggestion_pushed" in types
        assert "L1-07:redline_scan_completed" in types

    @pytest.mark.asyncio
    async def test_filter_by_types(
        self,
        adapter: L109EventBusAdapter,
    ) -> None:
        pid = "proj-real03"
        await adapter.append_event(
            project_id=pid,
            type="L1-07:suggestion_pushed",
            payload={"x": 1},
        )
        await adapter.append_event(
            project_id=pid,
            type="L1-07:redline_scan_completed",
            payload={"x": 2},
        )
        evs = await adapter.read_event_stream(
            pid, types=["L1-07:redline_scan_completed"]
        )
        assert len(evs) == 1


class TestHaltWithRealBus:
    @pytest.mark.asyncio
    async def test_halt_request_writes_to_real_bus(
        self, adapter: L109EventBusAdapter
    ) -> None:
        """验证 HaltRequester 用真实 L1-09 bus 也能 append L1-01:hard_halted。"""
        pid = "proj-real-halt"
        halt_target = MockHardHaltTarget()
        hr = HaltRequester(session_pid=pid, target=halt_target, event_bus=adapter)
        cmd = RequestHardHaltCommand(
            halt_id="halt-realtest-001",
            project_id=pid,
            red_line_id="HRL-TEST",
            evidence=HardHaltEvidence(
                observation_refs=("ev-real",),
                confirmation_count=2,
            ),
            ts="2026-04-23T00:00:00+00:00",
        )
        ack = await hr.request_hard_halt(cmd)
        assert ack.halted is True

        evs = await adapter.read_event_stream(pid)
        types = {e.type for e in evs}
        assert "L1-01:hard_halted" in types
