"""L2-01 聚合根 · EightDimensionCollector · 三入口统一门面。

- tick_collect：30s 周期 · 8 维全扫 · FULL / SOME_DIM_MISSING / STALE_WARNING 降级
- post_tool_use_fast_collect：PostToolUse hook · 500ms 硬锁 · 仅刷 tool_calls + latency_slo（下一 task 实现）
- on_demand_collect：UI / CLI 查询 · cache hit 路径 · dim_mask 部分采集（下一 task 实现）

IC-09 事件发射：每次采集完 append `L1-07:snapshot_captured` · payload 含 snapshot_id + degradation_level + trigger + latency。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.supervisor.common.clock import Clock
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ids import SnapshotId
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import (
    DegradationLevel,
    EightDimensionVector,
    SupervisorSnapshot,
    TriggerSource,
)
from app.supervisor.dim_collector.state_cache import StateCache


@dataclass
class EightDimensionCollector:
    """三入口采集门面。依赖注入 scanner / cache / event_bus / clock · 便于测试。"""

    scanner: DimScanner
    cache: StateCache
    event_bus: EventBusStub
    clock: Clock

    async def tick_collect(self, project_id: str) -> SupervisorSnapshot:
        """30s 周期全扫。SLO P99 ≤ 5s（stub 场景 ≤ 500ms）。"""
        if not project_id:
            raise ValueError("project_id is required (PM-14)")

        start_ms = self.clock.monotonic_ms()
        results = await self.scanner.scan_all(project_id)

        vector_kwargs: dict[str, Any] = {}
        reason_map: dict[str, str] = {}
        for dim_name, (value, err) in results.items():
            vector_kwargs[dim_name] = value
            if err is not None:
                reason_map[dim_name] = err.value

        vector = EightDimensionVector(**vector_kwargs)
        deg = _infer_degradation_level(vector.present_count, is_fast=False)
        end_ms = self.clock.monotonic_ms()

        snap = SupervisorSnapshot(
            project_id=project_id,
            snapshot_id=SnapshotId.generate().value,
            captured_at_ms=end_ms,
            trigger=TriggerSource.TICK,
            eight_dim_vector=vector,
            degradation_level=deg,
            degradation_reason_map=reason_map,
            evidence_refs=(),
            collection_latency_ms=max(0, end_ms - start_ms),
        )
        self.cache.put(snap)
        await self._emit_snapshot_captured(snap)
        return snap

    async def _emit_snapshot_captured(self, snap: SupervisorSnapshot) -> None:
        """IC-09 append 到 supervisor_events 子命名空间（stub 内共享存储）。"""
        await self.event_bus.append_event(
            project_id=snap.project_id,
            type="L1-07:snapshot_captured",
            payload={
                "snapshot_id": snap.snapshot_id,
                "degradation_level": snap.degradation_level.value,
                "trigger": snap.trigger.value,
                "collection_latency_ms": snap.collection_latency_ms,
                "vector_schema_version": snap.vector_schema_version,
            },
        )


def _infer_degradation_level(present_count: int, *, is_fast: bool) -> DegradationLevel:
    """根据 present 维度数推 degradation_level。

    - 8 维全 present · FAST 上下文 → FULL_FAST（表明 6 维 from cache）
    - 8 维全 present · TICK/ON_DEMAND 上下文 → FULL
    - 0 维 present → STALE_WARNING（外层可降级到 LAST_KNOWN_GOOD 若 LKG 有效）
    - 1-7 维 present → SOME_DIM_MISSING
    """
    if present_count == 8:
        return DegradationLevel.FULL_FAST if is_fast else DegradationLevel.FULL
    if present_count == 0:
        return DegradationLevel.STALE_WARNING
    return DegradationLevel.SOME_DIM_MISSING
