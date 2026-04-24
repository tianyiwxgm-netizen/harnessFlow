"""L2-01 聚合根 · EightDimensionCollector · 三入口统一门面。

- tick_collect：30s 周期 · 8 维全扫 · FULL / SOME_DIM_MISSING / STALE_WARNING 降级
- post_tool_use_fast_collect：PostToolUse hook · 500ms 硬锁 · 仅刷 tool_calls + latency_slo · 其他 6 维复用 LKG
- on_demand_collect：UI / CLI 查询 · cache hit 路径 + dim_mask 部分采集

IC-09 事件发射：每次采集完 append `L1-07:snapshot_captured` · payload 含 snapshot_id + degradation_level + trigger + latency。
"""
from __future__ import annotations

import asyncio
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


_DIM_KEYS = (
    "phase",
    "artifacts",
    "wp_status",
    "tool_calls",
    "latency_slo",
    "self_repair_rate",
    "rollback_counter",
    "event_bus",
)

_FAST_REFRESHED_DIMS = ("tool_calls", "latency_slo")


@dataclass
class EightDimensionCollector:
    """三入口采集门面。依赖注入 scanner / cache / event_bus / clock · 便于测试。"""

    scanner: DimScanner
    cache: StateCache
    event_bus: EventBusStub
    clock: Clock

    # ------------------------------------------------------------------ tick
    async def tick_collect(self, project_id: str) -> SupervisorSnapshot:
        """30s 周期全扫。SLO P99 ≤ 5s（stub 场景 ≤ 500ms）。"""
        self._require_pid(project_id)
        start_ms = self.clock.monotonic_ms()
        results = await self.scanner.scan_all(project_id)

        vector_kwargs, reason_map, dim_refs = self._build_vector_from_results(results)
        vector = EightDimensionVector(
            **vector_kwargs,
            dim_evidence_refs=dim_refs,
        )
        deg = _infer_degradation_level(vector.present_count, is_fast=False)

        snap = self._make_snapshot(
            project_id=project_id,
            trigger=TriggerSource.TICK,
            vector=vector,
            deg=deg,
            reason_map=reason_map,
            start_ms=start_ms,
            metrics={},
            dim_refs=dim_refs,
        )
        self.cache.put(snap)
        await self._emit_snapshot_captured(snap)
        return snap

    # ---------------------------------------------------------------- fast
    async def post_tool_use_fast_collect(
        self,
        project_id: str,
        tool_name: str,
        tool_args_hash: str,
        tool_invoked_at_iso: str,
        hook_deadline_ms: int = 500,
    ) -> SupervisorSnapshot:
        """PostToolUse hook 入口 · 500ms 硬锁 · 只刷 tool_calls + latency_slo。"""
        self._require_pid(project_id)
        start_ms = self.clock.monotonic_ms()

        # 并行刷 2 维
        tc_res, lt_res = await asyncio.gather(
            self.scanner.scan_tool_calls(project_id),
            self.scanner.scan_latency_slo(project_id),
        )
        tc_val, tc_refs, tc_err = tc_res
        lt_val, lt_refs, lt_err = lt_res

        reason_map: dict[str, str] = {}
        if tc_err is not None:
            reason_map["tool_calls"] = tc_err.value
        if lt_err is not None:
            reason_map["latency_slo"] = lt_err.value

        # 6 维从 LKG 复用（dim_evidence_refs 同复用 · 新刷 2 维覆盖）
        cached = self.cache.get_latest(project_id)
        if cached is not None:
            new_dim_refs = dict(cached.eight_dim_vector.dim_evidence_refs)
            new_dim_refs["tool_calls"] = tc_refs
            new_dim_refs["latency_slo"] = lt_refs
            vector = cached.eight_dim_vector.model_copy(
                update={
                    "tool_calls": tc_val,
                    "latency_slo": lt_val,
                    "dim_evidence_refs": new_dim_refs,
                }
            )
        else:
            new_dim_refs = {"tool_calls": tc_refs, "latency_slo": lt_refs}
            vector = EightDimensionVector(
                tool_calls=tc_val,
                latency_slo=lt_val,
                dim_evidence_refs=new_dim_refs,
            )
            for missing in _DIM_KEYS:
                if missing in _FAST_REFRESHED_DIMS:
                    continue
                reason_map.setdefault(missing, "E_NO_CACHE_AVAILABLE")

        if cached is not None and vector.present_count == 8:
            deg = DegradationLevel.FULL_FAST
        elif vector.present_count == 0:
            deg = DegradationLevel.STALE_WARNING
        else:
            deg = DegradationLevel.SOME_DIM_MISSING

        snap = self._make_snapshot(
            project_id=project_id,
            trigger=TriggerSource.POST_TOOL_USE,
            vector=vector,
            deg=deg,
            reason_map=reason_map,
            start_ms=start_ms,
            metrics={
                "tool_name": tool_name,
                "tool_args_hash": tool_args_hash,
                "tool_invoked_at": tool_invoked_at_iso,
                "hook_deadline_ms": hook_deadline_ms,
            },
            dim_refs=dict(vector.dim_evidence_refs),
        )
        # fast 路径也更新 cache · 让下次 fast 或 on_demand 拿到 fresh tool_calls
        self.cache.put(snap)
        await self._emit_snapshot_captured(snap)
        return snap

    # ----------------------------------------------------------- on_demand
    async def on_demand_collect(
        self,
        project_id: str,
        consumer_id: str,
        max_staleness_sec: int = 60,
        dim_mask: dict[str, bool] | None = None,
    ) -> SupervisorSnapshot:
        """UI / CLI 查询入口。

        - cache hit 且未过 max_staleness_sec · 无 dim_mask → 直接返 cached（P95 ≤ 20ms）
        - cache miss / max_staleness=0 / dim_mask 指定 → 做 targeted scan
        """
        self._require_pid(project_id)

        # cache-hit fast path
        cached = self.cache.get_latest(project_id)
        now = self.clock.monotonic_ms()
        if (
            max_staleness_sec > 0
            and dim_mask is None
            and cached is not None
            and (now - cached.captured_at_ms) <= max_staleness_sec * 1000
        ):
            return cached.model_copy(
                update={
                    "trigger": TriggerSource.ON_DEMAND,
                    "metrics": {
                        **cached.metrics,
                        "cache_hit": True,
                        "consumer_id": consumer_id,
                    },
                }
            )

        start_ms = now
        results = await self._scan_with_mask(project_id, dim_mask)
        vector_kwargs, reason_map, dim_refs = self._build_vector_from_results(results)
        vector = EightDimensionVector(
            **vector_kwargs,
            dim_evidence_refs=dim_refs,
        )

        if dim_mask is None:
            deg = _infer_degradation_level(vector.present_count, is_fast=False)
        else:
            # partial request · degradation follows what was asked
            deg = (
                DegradationLevel.FULL
                if vector.present_count >= sum(1 for v in dim_mask.values() if v)
                else DegradationLevel.SOME_DIM_MISSING
            )

        snap = self._make_snapshot(
            project_id=project_id,
            trigger=TriggerSource.ON_DEMAND,
            vector=vector,
            deg=deg,
            reason_map=reason_map,
            start_ms=start_ms,
            metrics={
                "consumer_id": consumer_id,
                "cache_hit": False,
                "dim_mask": dim_mask or {},
            },
            dim_refs=dim_refs,
        )
        # 只有全扫时才写 LKG cache（避免部分向量污染）
        if dim_mask is None:
            self.cache.put(snap)
        await self._emit_snapshot_captured(snap)
        return snap

    # ----------------------------------------------------------- helpers
    @staticmethod
    def _require_pid(project_id: str) -> None:
        if not project_id:
            raise ValueError("project_id is required (PM-14)")

    @staticmethod
    def _build_vector_from_results(
        results: dict[str, Any],  # value: DimScanResult NamedTuple
    ) -> tuple[dict[str, Any], dict[str, str], dict[str, tuple[str, ...]]]:
        kwargs: dict[str, Any] = {}
        reasons: dict[str, str] = {}
        dim_refs: dict[str, tuple[str, ...]] = {}
        for dim_name, res in results.items():
            # DimScanResult NamedTuple 支持 3 元组拆包
            value, evidence_refs, err = res
            kwargs[dim_name] = value
            if err is not None:
                reasons[dim_name] = err.value
            # evidence_refs 总是记录（失败时为空 tuple · 保留 key）
            dim_refs[dim_name] = tuple(evidence_refs)
        return kwargs, reasons, dim_refs

    async def _scan_with_mask(
        self, project_id: str, dim_mask: dict[str, bool] | None
    ) -> dict[str, Any]:
        if dim_mask is None:
            return await self.scanner.scan_all(project_id)

        # partial parallel scan
        selected: list[tuple[str, Any]] = []
        for key in _DIM_KEYS:
            if dim_mask.get(key, False):
                coro = getattr(self.scanner, f"scan_{key}")(project_id)
                selected.append((key, coro))

        # import local to avoid circular
        from app.supervisor.dim_collector.dim_scanner import DimScanResult

        empty = DimScanResult(None, (), None)
        if not selected:
            return {k: empty for k in _DIM_KEYS}

        keys = [k for k, _ in selected]
        coros = [c for _, c in selected]
        partials = dict(zip(keys, await asyncio.gather(*coros)))

        out: dict[str, Any] = {}
        for k in _DIM_KEYS:
            out[k] = partials.get(k, empty)
        return out

    def _make_snapshot(
        self,
        *,
        project_id: str,
        trigger: TriggerSource,
        vector: EightDimensionVector,
        deg: DegradationLevel,
        reason_map: dict[str, str],
        start_ms: int,
        metrics: dict[str, Any],
        dim_refs: dict[str, tuple[str, ...]] | None = None,
    ) -> SupervisorSnapshot:
        end_ms = self.clock.monotonic_ms()
        # 总 evidence_refs = 各维 refs union（去重保序）
        if dim_refs is None:
            dim_refs = dict(vector.dim_evidence_refs)
        all_refs: list[str] = []
        seen: set[str] = set()
        for _, refs in dim_refs.items():
            for r in refs:
                if r not in seen:
                    seen.add(r)
                    all_refs.append(r)
        return SupervisorSnapshot(
            project_id=project_id,
            snapshot_id=SnapshotId.generate().value,
            captured_at_ms=end_ms,
            trigger=trigger,
            eight_dim_vector=vector,
            degradation_level=deg,
            degradation_reason_map=reason_map,
            evidence_refs=tuple(all_refs),
            collection_latency_ms=max(0, end_ms - start_ms),
            metrics=metrics,
        )

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

    - 8 维全 present · FAST 上下文 → FULL_FAST
    - 8 维全 present · TICK/ON_DEMAND 上下文 → FULL
    - 0 维 present → STALE_WARNING
    - 1-7 维 present → SOME_DIM_MISSING
    """
    if present_count == 8:
        return DegradationLevel.FULL_FAST if is_fast else DegradationLevel.FULL
    if present_count == 0:
        return DegradationLevel.STALE_WARNING
    return DegradationLevel.SOME_DIM_MISSING
