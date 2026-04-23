"""8 维独立 scanner + per-dim 错误隔离。

每个 scanner：
- 正常返回 (value, None)
- 失败返回 (None, SupervisorError)
单维失败绝不抛出 · 交由 collector 聚合为 degradation_reason_map。

scan_all 用 asyncio.gather 并行 · 按 keys 顺序映射结果。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from app.supervisor.common.errors import SupervisorError
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub

DimResult = tuple[Any | None, SupervisorError | None]

_RED_LINE_CANDIDATE_TOOLS = frozenset({"git", "rm", "deploy"})
_DEFAULT_LATENCY_SLO_MS = 2000


@dataclass
class DimScanner:
    """8 维度独立采集器 · 注入 IC stubs + event bus。"""

    l102: L102Stub
    l103: L103Stub
    l104: L104Stub
    event_bus: EventBusStub

    async def scan_phase(self, project_id: str) -> DimResult:
        try:
            out = await self.l102.read_lifecycle_state(project_id)
        except TimeoutError:
            return None, SupervisorError.IC_L1_02_TIMEOUT
        except Exception:
            return None, SupervisorError.IC_L1_02_UNAVAILABLE
        return out.get("phase"), None

    async def scan_artifacts(self, project_id: str) -> DimResult:
        try:
            out = await self.l102.read_stage_artifacts(project_id)
        except TimeoutError:
            return None, SupervisorError.IC_L1_02_TIMEOUT
        except Exception:
            return None, SupervisorError.IC_L1_02_UNAVAILABLE
        return out, None

    async def scan_wp_status(self, project_id: str) -> DimResult:
        try:
            out = await self.l103.read_wbs_snapshot(project_id)
        except TimeoutError:
            return None, SupervisorError.IC_L1_03_TIMEOUT
        except Exception:
            return None, SupervisorError.IC_L1_03_UNAVAILABLE
        return out, None

    async def scan_self_repair_rate(self, project_id: str) -> DimResult:
        try:
            out = await self.l104.read_self_repair_stats(project_id)
        except TimeoutError:
            return None, SupervisorError.IC_L1_04_TIMEOUT
        except Exception:
            return None, SupervisorError.IC_L1_04_UNAVAILABLE
        return out, None

    async def scan_rollback_counter(self, project_id: str) -> DimResult:
        try:
            out = await self.l104.read_rollback_counter(project_id)
        except TimeoutError:
            return None, SupervisorError.IC_L1_04_TIMEOUT
        except Exception:
            return None, SupervisorError.IC_L1_04_UNAVAILABLE
        return out, None

    async def scan_event_bus(self, project_id: str) -> DimResult:
        try:
            stats = await self.event_bus.read_event_bus_stats(project_id, window_sec=30)
        except Exception:
            return None, SupervisorError.IC_L1_09_UNAVAILABLE
        return stats, None

    async def scan_tool_calls(self, project_id: str) -> DimResult:
        try:
            evs = await self.event_bus.read_event_stream(
                project_id=project_id, types=["tool_invoked"], window_sec=60
            )
        except Exception:
            return None, SupervisorError.IC_L1_09_UNAVAILABLE
        if not evs:
            return {
                "last_tool_name": None,
                "red_line_candidate": False,
                "last_n_calls": [],
            }, None
        last = evs[-1]
        recent = evs[-10:]
        candidate = any(
            e.payload.get("tool_name", "") in _RED_LINE_CANDIDATE_TOOLS for e in recent
        )
        return {
            "last_tool_name": last.payload.get("tool_name"),
            "red_line_candidate": candidate,
            "last_n_calls": [
                {
                    "tool": e.payload.get("tool_name"),
                    "ts_ms": e.triggered_at_ms,
                    "args_hash": e.payload.get("args_hash"),
                }
                for e in recent
            ],
        }, None

    async def scan_latency_slo(self, project_id: str) -> DimResult:
        try:
            evs = await self.event_bus.read_event_stream(
                project_id=project_id, types=["latency_sample"], window_sec=60
            )
        except Exception:
            return None, SupervisorError.IC_L1_09_UNAVAILABLE
        if not evs:
            return {
                "slo_target_ms": _DEFAULT_LATENCY_SLO_MS,
                "actual_p95_ms": None,
                "actual_p99_ms": None,
                "compliance_rate": None,
            }, None
        samples = sorted(int(e.payload.get("dur_ms", 0)) for e in evs)
        n = len(samples)
        p95 = samples[min(n - 1, int(0.95 * n))]
        p99 = samples[min(n - 1, int(0.99 * n))]
        compliance = sum(1 for s in samples if s <= _DEFAULT_LATENCY_SLO_MS) / n
        return {
            "slo_target_ms": _DEFAULT_LATENCY_SLO_MS,
            "actual_p95_ms": p95,
            "actual_p99_ms": p99,
            "compliance_rate": round(compliance, 4),
        }, None

    async def scan_all(self, project_id: str) -> dict[str, DimResult]:
        """8 维并行 · 按 dim key 返回。单维失败不影响他维。"""
        keys = (
            "phase",
            "artifacts",
            "wp_status",
            "tool_calls",
            "latency_slo",
            "self_repair_rate",
            "rollback_counter",
            "event_bus",
        )
        coros = [
            self.scan_phase(project_id),
            self.scan_artifacts(project_id),
            self.scan_wp_status(project_id),
            self.scan_tool_calls(project_id),
            self.scan_latency_slo(project_id),
            self.scan_self_repair_rate(project_id),
            self.scan_rollback_counter(project_id),
            self.scan_event_bus(project_id),
        ]
        results = await asyncio.gather(*coros)
        return dict(zip(keys, results))
