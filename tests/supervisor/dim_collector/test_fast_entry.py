"""post_tool_use_fast_collect · PostToolUse hook · 500ms 硬锁。

契约：
- 仅刷 tool_calls (dim_4) + latency_slo (dim_5)
- 其他 6 维从 LKG cache 复用
- cache miss 时：仅填 2 维 · 标记 SOME_DIM_MISSING
- cache hit 且两维成功：标记 FULL_FAST
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


def _build(clock: FrozenClock | None = None, bus: EventBusStub | None = None) -> EightDimensionCollector:
    bus = bus or EventBusStub()
    clock = clock or FrozenClock()
    scanner = DimScanner(
        l102=L102Stub(), l103=L103Stub(), l104=L104Stub(), event_bus=bus
    )
    cache = StateCache(clock=clock, ttl_ms=60_000)
    return EightDimensionCollector(
        scanner=scanner, cache=cache, event_bus=bus, clock=clock
    )


async def test_fast_collect_sets_trigger_post_tool_use(pid) -> None:
    c = _build()
    snap = await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="git",
        tool_args_hash="abc",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    assert snap.trigger == TriggerSource.POST_TOOL_USE


async def test_fast_collect_reuses_cached_six_dims(pid) -> None:
    clock = FrozenClock()
    c = _build(clock=clock)
    # seed tick snapshot with phase=S3 + wp_status
    tick = await c.tick_collect(project_id=pid.value)
    assert tick.eight_dim_vector.phase == "S3"
    clock.advance(100)

    fast = await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="rm",
        tool_args_hash="h",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    # 2 fresh dims (tool_calls + latency_slo)
    assert fast.eight_dim_vector.tool_calls is not None
    assert fast.eight_dim_vector.latency_slo is not None
    # 6 reused dims (phase/artifacts/wp_status/self_repair_rate/rollback_counter/event_bus)
    assert fast.eight_dim_vector.phase == "S3"
    assert fast.eight_dim_vector.wp_status is not None


async def test_fast_collect_full_fast_level_when_cache_hit(pid) -> None:
    c = _build()
    await c.tick_collect(project_id=pid.value)
    fast = await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="git",
        tool_args_hash="h",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    assert fast.degradation_level == DegradationLevel.FULL_FAST


async def test_fast_collect_some_dim_missing_without_cache(pid) -> None:
    c = _build()
    fast = await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="git",
        tool_args_hash="h",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    assert fast.degradation_level == DegradationLevel.SOME_DIM_MISSING
    assert fast.eight_dim_vector.phase is None  # no cache to reuse
    assert "no_cache" in fast.degradation_reason_map.get("phase", "").lower() or fast.degradation_reason_map.get("phase")


async def test_fast_collect_records_tool_metadata_in_metrics(pid) -> None:
    c = _build()
    snap = await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="git",
        tool_args_hash="deadbeef",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    assert snap.metrics.get("tool_name") == "git"
    assert snap.metrics.get("tool_args_hash") == "deadbeef"
    assert snap.metrics.get("hook_deadline_ms") == 500


async def test_fast_collect_rejects_empty_pid(pid) -> None:
    c = _build()
    with pytest.raises(ValueError, match="project_id"):
        await c.post_tool_use_fast_collect(
            project_id="",
            tool_name="git",
            tool_args_hash="h",
            tool_invoked_at_iso="2026-04-23T00:00:01Z",
            hook_deadline_ms=500,
        )


async def test_fast_collect_emits_snapshot_captured_event(pid) -> None:
    bus = EventBusStub()
    c = _build(bus=bus)
    await c.post_tool_use_fast_collect(
        project_id=pid.value,
        tool_name="git",
        tool_args_hash="h",
        tool_invoked_at_iso="2026-04-23T00:00:01Z",
        hook_deadline_ms=500,
    )
    evs = await bus.read_event_stream(
        project_id=pid.value,
        types=["L1-07:snapshot_captured"],
        window_sec=60,
    )
    post_use_events = [e for e in evs if e.payload.get("trigger") == "POST_TOOL_USE"]
    assert len(post_use_events) == 1
