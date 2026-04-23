"""EightDimensionCollector.tick_collect (30s 周期全扫) 契约测试。

覆盖：
- 正常路径：8 维全 present → DegradationLevel.FULL
- 事件发射：snapshot_captured 进入 IC-09 命名空间
- PM-14：pid 空串必拒
- 降级：l102 timeout → SOME_DIM_MISSING + reason_map
- 全缺：所有 IC 挂 → STALE_WARNING
- LKG 写入：snapshot put 到 cache
"""
from __future__ import annotations

import pytest

from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import DegradationLevel, TriggerSource
from app.supervisor.dim_collector.state_cache import StateCache


pytestmark = pytest.mark.asyncio


def _build(
    l102: L102Stub | None = None,
    l103: L103Stub | None = None,
    l104: L104Stub | None = None,
    bus: EventBusStub | None = None,
    clock: FrozenClock | None = None,
) -> EightDimensionCollector:
    bus = bus or EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(
        l102=l102 or L102Stub(),
        l103=l103 or L103Stub(),
        l104=l104 or L104Stub(),
        event_bus=bus,
    )
    cache = StateCache(clock=clock, ttl_ms=60_000)
    return EightDimensionCollector(
        scanner=scanner, cache=cache, event_bus=bus, clock=clock
    )


async def test_tick_collect_returns_snapshot_with_trigger_tick(pid) -> None:
    c = _build()
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.project_id == pid.value
    assert snap.trigger == TriggerSource.TICK


async def test_tick_collect_full_degradation_when_all_ics_healthy(pid) -> None:
    c = _build()
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_level == DegradationLevel.FULL
    assert snap.eight_dim_vector.present_count == 8
    assert snap.degradation_reason_map == {}


async def test_tick_collect_populates_phase_from_l102(pid) -> None:
    c = _build(l102=L102Stub(phase="S5"))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.eight_dim_vector.phase == "S5"


async def test_tick_collect_emits_snapshot_captured_event(pid) -> None:
    bus = EventBusStub()
    c = _build(bus=bus)
    snap = await c.tick_collect(project_id=pid.value)
    events = await bus.read_event_stream(
        project_id=pid.value,
        types=["L1-07:snapshot_captured"],
        window_sec=60,
    )
    assert len(events) == 1
    payload = events[0].payload
    assert payload["snapshot_id"] == snap.snapshot_id
    assert payload["degradation_level"] == "FULL"
    assert payload["trigger"] == "TICK"


async def test_tick_collect_persists_to_cache(pid) -> None:
    c = _build()
    snap = await c.tick_collect(project_id=pid.value)
    latest = c.cache.get_latest(pid.value)
    assert latest is not None
    assert latest.snapshot_id == snap.snapshot_id


async def test_tick_collect_rejects_empty_pid_pm14() -> None:
    c = _build()
    with pytest.raises(ValueError, match="project_id"):
        await c.tick_collect(project_id="")


async def test_tick_collect_degrades_to_some_dim_missing_on_l102_timeout(
    pid,
) -> None:
    c = _build(l102=L102Stub(_timeout=True))
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_level == DegradationLevel.SOME_DIM_MISSING
    assert snap.eight_dim_vector.phase is None
    assert snap.eight_dim_vector.artifacts is None
    assert (
        snap.degradation_reason_map["phase"] == "E_IC_L1_02_TIMEOUT"
    )
    assert (
        snap.degradation_reason_map["artifacts"] == "E_IC_L1_02_TIMEOUT"
    )
    # non-l102 dims untouched
    assert snap.eight_dim_vector.wp_status is not None


async def test_tick_collect_records_snapshot_id_format(pid) -> None:
    c = _build()
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.snapshot_id.startswith("snap-")


async def test_tick_collect_latency_ms_non_negative(pid) -> None:
    c = _build()
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.collection_latency_ms >= 0


async def test_tick_collect_stale_warning_when_all_ics_fail(pid) -> None:
    """所有 IC 挂掉 + event_bus 挂掉 → 8 维全 None → STALE_WARNING。"""
    bus = EventBusStub()
    clock = FrozenClock()
    scanner = DimScanner(
        l102=L102Stub(_unavailable=True),
        l103=L103Stub(_unavailable=True),
        l104=L104Stub(_unavailable=True),
        event_bus=bus,
    )

    # Break event_bus methods so scan_tool_calls/latency_slo/event_bus all fail
    async def _boom(*args, **kwargs):
        raise RuntimeError("event bus down")

    scanner.event_bus = type("Broken", (), {
        "read_event_stream": _boom,
        "read_event_bus_stats": _boom,
        "append_event": bus.append_event,  # collector still needs to emit
    })()

    cache = StateCache(clock=clock, ttl_ms=60_000)
    c = EightDimensionCollector(
        scanner=scanner, cache=cache, event_bus=bus, clock=clock
    )
    snap = await c.tick_collect(project_id=pid.value)
    assert snap.degradation_level == DegradationLevel.STALE_WARNING
    assert snap.eight_dim_vector.present_count == 0
    # all 8 dims should have error reasons
    assert len(snap.degradation_reason_map) == 8
