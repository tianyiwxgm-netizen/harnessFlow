"""IC-12 · emit_metric (8 维度采集) 集成测试 · 5 TC.

(WP04 任务表 IC-12 重映射 = L1-07 EightDimensionCollector + IC-09 联动)

覆盖:
    TC-1 8 维采集: tick_collect → 8 维全 present + DegradationLevel.FULL
    TC-2 SLO: tick 采集 P95 ≤ 500ms (stub 远低)
    TC-3 越界: 空 pid → ValueError (PM-14 守护)
    TC-4 snapshot 写 cache · 后续 get_latest 可读
    TC-5 IC-09 联动: snapshot_captured 事件 emit · payload 含 snapshot_id + trigger
"""
from __future__ import annotations

import asyncio
import time

import pytest

from app.supervisor.dim_collector.schemas import DegradationLevel, TriggerSource


def run_async(coro):
    return asyncio.run(coro)


class TestIC12Integration:
    """IC-12 集成 · 8 维 collector + IC-09 audit."""

    # ---- TC-1 · 8 维采集: 全 present + FULL ----
    def test_8_dim_collected_full_degradation(
        self, collector, project_id: str,
    ) -> None:
        snap = run_async(collector.tick_collect(project_id=project_id))

        assert snap.project_id == project_id
        assert snap.trigger == TriggerSource.TICK
        # IC-12 §3.12 8 维全 present · degradation_level=FULL
        assert snap.degradation_level == DegradationLevel.FULL
        assert snap.eight_dim_vector.present_count == 8
        assert snap.degradation_reason_map == {}

    # ---- TC-2 · SLO P95 ≤ 500ms ----
    def test_slo_tick_p95_within_500ms(
        self, collector, project_id: str,
    ) -> None:
        latencies: list[float] = []
        for _ in range(10):
            t0 = time.perf_counter()
            snap = run_async(collector.tick_collect(project_id=project_id))
            latencies.append((time.perf_counter() - t0) * 1000.0)
            assert snap.project_id == project_id

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        # IC-12 §3.12 tick SLO 500ms (stub 路径远低)
        assert p95 < 500.0, f"IC-12 P95 SLO 超时 {p95:.1f}ms"

    # ---- TC-3 · 越界: 空 pid PM-14 守护 ----
    def test_empty_pid_rejected(self, collector) -> None:
        with pytest.raises((ValueError, AssertionError)):
            run_async(collector.tick_collect(project_id=""))

    # ---- TC-4 · snapshot 写 cache · get_latest 可读 ----
    def test_snapshot_persisted_in_cache(
        self, collector, project_id: str,
    ) -> None:
        snap = run_async(collector.tick_collect(project_id=project_id))

        # cache 写入 · get_latest 应返同 snapshot
        cached = collector.cache.get_latest(project_id)
        assert cached is not None
        assert cached.snapshot_id == snap.snapshot_id
        assert cached.project_id == project_id

    # ---- TC-5 · IC-09 联动: snapshot_captured 事件 emit ----
    def test_ic09_snapshot_captured_emitted(
        self, collector, event_bus_stub, project_id: str,
    ) -> None:
        snap = run_async(collector.tick_collect(project_id=project_id))

        events = run_async(event_bus_stub.read_event_stream(
            project_id=project_id,
            types=["L1-07:snapshot_captured"],
            window_sec=60,
        ))
        assert len(events) == 1
        payload = events[0].payload
        # IC-12 §3.12 snapshot_captured payload 含 snapshot_id + trigger
        assert payload["snapshot_id"] == snap.snapshot_id
        assert payload["trigger"] == TriggerSource.TICK.value
