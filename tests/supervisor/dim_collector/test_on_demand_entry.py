"""on_demand_collect · UI / CLI 查询入口。

契约：
- cache hit + 未过 staleness → 直接返 cached（20ms P95）
- max_staleness_sec = 0 → 强制 fresh scan
- dim_mask 非 None → 仅扫指定维 · 不写 LKG
- 事件仍发射
"""
from __future__ import annotations

import pytest

from app.supervisor.common.clock import FrozenClock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import TriggerSource
from app.supervisor.dim_collector.state_cache import StateCache


pytestmark = pytest.mark.asyncio


def _build(clock: FrozenClock | None = None) -> EightDimensionCollector:
    bus = EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(
        l102=L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus
    )
    return EightDimensionCollector(
        scanner=scanner,
        cache=StateCache(clock=clock, ttl_ms=60_000),
        event_bus=bus,
        clock=clock,
    )


async def test_on_demand_cache_hit_returns_cached_id(pid) -> None:
    clock = FrozenClock()
    c = _build(clock=clock)
    orig = await c.tick_collect(project_id=pid.value)
    clock.advance(1_000)
    snap = await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="l1-10-ui-1",
        max_staleness_sec=60,
    )
    assert snap.snapshot_id == orig.snapshot_id
    assert snap.trigger == TriggerSource.ON_DEMAND
    assert snap.metrics.get("cache_hit") is True
    assert snap.metrics.get("consumer_id") == "l1-10-ui-1"


async def test_on_demand_forces_fresh_when_staleness_zero(pid) -> None:
    c = _build()
    snap = await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="cli-1",
        max_staleness_sec=0,
    )
    assert snap.eight_dim_vector.phase == "S3"
    # metrics.cache_hit should be False for forced fresh
    assert snap.metrics.get("cache_hit") is False


async def test_on_demand_dim_mask_scans_only_selected(pid) -> None:
    c = _build()
    snap = await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="cli-2",
        max_staleness_sec=0,
        dim_mask={
            "phase": True,
            "wp_status": True,
            "artifacts": False,
            "tool_calls": False,
            "latency_slo": False,
            "self_repair_rate": False,
            "rollback_counter": False,
            "event_bus": False,
        },
    )
    assert snap.eight_dim_vector.phase == "S3"
    assert snap.eight_dim_vector.wp_status is not None
    assert snap.eight_dim_vector.artifacts is None
    assert snap.eight_dim_vector.tool_calls is None


async def test_on_demand_dim_mask_does_not_pollute_cache(pid) -> None:
    c = _build()
    await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="cli-3",
        max_staleness_sec=0,
        dim_mask={"phase": True},
    )
    # cache should still be empty (partial scan not cached)
    assert c.cache.get_latest(pid.value) is None


async def test_on_demand_refreshes_after_ttl(pid) -> None:
    clock = FrozenClock()
    c = _build(clock=clock)
    await c.tick_collect(project_id=pid.value)
    # force staleness: max < elapsed
    clock.advance(5_000)
    snap = await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="ui-2",
        max_staleness_sec=1,  # 1 second allowed · 5s elapsed → miss
    )
    # cache miss forces fresh scan
    assert snap.metrics.get("cache_hit") is False


async def test_on_demand_emits_snapshot_captured_event(pid) -> None:
    c = _build()
    await c.on_demand_collect(
        project_id=pid.value,
        consumer_id="cli-4",
        max_staleness_sec=0,
    )
    evs = await c.event_bus.read_event_stream(
        project_id=pid.value,
        types=["L1-07:snapshot_captured"],
        window_sec=60,
    )
    on_demand_events = [e for e in evs if e.payload.get("trigger") == "ON_DEMAND"]
    assert len(on_demand_events) == 1


async def test_on_demand_rejects_empty_pid() -> None:
    c = _build()
    with pytest.raises(ValueError, match="project_id"):
        await c.on_demand_collect(
            project_id="",
            consumer_id="cli-x",
            max_staleness_sec=60,
        )
