"""8 维独立 scanner + per-dim 错误隔离 + per-dim evidence_refs（追溯粒度）。

每个 scanner：
- 正常返回 (value, evidence_refs, None)
- 失败返回 (None, (), SupervisorError)
单维失败绝不抛出 · 交由 collector 聚合为 degradation_reason_map。

evidence_refs 设计（tech-design §2.2 + PRD §8.4 硬约束）：
- 每维值必须可追溯到产生它的源事件 id（event_bus / IC stub 返回）
- L1-02/L1-03/L1-04 stub 场景 · 用合成 synthetic ref `"ic:<IC_NAME>:<pid>:<epoch>"`
- L1-09 read_event_stream 场景 · 直接取命中事件的 event_id

scan_all 用 asyncio.gather 并行 · 按 keys 顺序映射结果。
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, NamedTuple

from app.supervisor.common.errors import SupervisorError
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub


class DimScanResult(NamedTuple):
    """单维采集三要素：值 · 证据 · 错误。

    兼容原 `(value, err)` tuple 拆包模式 · 新增 evidence_refs 位于中间位置。
    使用 NamedTuple 便于 `.value / .evidence_refs / .err` 属性访问。
    """

    value: Any | None
    evidence_refs: tuple[str, ...]
    err: SupervisorError | None


# 保留旧别名（非新代码不建议用 · 但现有测试 15 处用 3 元组已直接拆包 · 无需别名）
DimResult = DimScanResult


def _synthetic_ref(ic: str, pid: str) -> str:
    """L1-02/L1-03/L1-04 stub 返回 · 为不丢审计链 · 生成合成 ref。

    格式：`ic:<IC_NAME>:<pid>:<ms>`。生产替代 · 真实 IC stub 会在响应里带 evidence_event_id。
    """
    return f"ic:{ic}:{pid}:{int(time.time() * 1000)}"

_RED_LINE_CANDIDATE_TOOLS = frozenset({"git", "rm", "deploy"})
_DEFAULT_LATENCY_SLO_MS = 2000


@dataclass
class DimScanner:
    """8 维度独立采集器 · 注入 IC stubs + event bus。"""

    l102: L102Stub
    l103: L103Stub
    l104: L104Stub
    event_bus: EventBusStub

    async def scan_phase(self, project_id: str) -> DimScanResult:
        try:
            out = await self.l102.read_lifecycle_state(project_id)
        except TimeoutError:
            return DimScanResult(None, (), SupervisorError.IC_L1_02_TIMEOUT)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_02_UNAVAILABLE)
        refs = (_synthetic_ref("IC-L1-02-read_lifecycle_state", project_id),)
        return DimScanResult(out.get("phase"), refs, None)

    async def scan_artifacts(self, project_id: str) -> DimScanResult:
        try:
            out = await self.l102.read_stage_artifacts(project_id)
        except TimeoutError:
            return DimScanResult(None, (), SupervisorError.IC_L1_02_TIMEOUT)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_02_UNAVAILABLE)
        refs = (_synthetic_ref("IC-L1-02-read_stage_artifacts", project_id),)
        return DimScanResult(out, refs, None)

    async def scan_wp_status(self, project_id: str) -> DimScanResult:
        try:
            out = await self.l103.read_wbs_snapshot(project_id)
        except TimeoutError:
            return DimScanResult(None, (), SupervisorError.IC_L1_03_TIMEOUT)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_03_UNAVAILABLE)
        refs = (_synthetic_ref("IC-L1-03-read_wbs_snapshot", project_id),)
        return DimScanResult(out, refs, None)

    async def scan_self_repair_rate(self, project_id: str) -> DimScanResult:
        try:
            out = await self.l104.read_self_repair_stats(project_id)
        except TimeoutError:
            return DimScanResult(None, (), SupervisorError.IC_L1_04_TIMEOUT)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_04_UNAVAILABLE)
        refs = (_synthetic_ref("IC-L1-04-read_self_repair_stats", project_id),)
        return DimScanResult(out, refs, None)

    async def scan_rollback_counter(self, project_id: str) -> DimScanResult:
        try:
            out = await self.l104.read_rollback_counter(project_id)
        except TimeoutError:
            return DimScanResult(None, (), SupervisorError.IC_L1_04_TIMEOUT)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_04_UNAVAILABLE)
        refs = (_synthetic_ref("IC-L1-04-read_rollback_counter", project_id),)
        return DimScanResult(out, refs, None)

    async def scan_event_bus(self, project_id: str) -> DimScanResult:
        try:
            stats = await self.event_bus.read_event_bus_stats(project_id, window_sec=30)
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_09_UNAVAILABLE)
        # stats 是聚合 summary · 证据用合成 ref（L1-09 side 无法逐 id 列举全窗口）
        refs = (_synthetic_ref("IC-L1-09-read_event_bus_stats", project_id),)
        return DimScanResult(stats, refs, None)

    async def scan_tool_calls(self, project_id: str) -> DimScanResult:
        try:
            evs = await self.event_bus.read_event_stream(
                project_id=project_id, types=["tool_invoked"], window_sec=60
            )
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_09_UNAVAILABLE)
        if not evs:
            empty_val = {
                "last_tool_name": None,
                "red_line_candidate": False,
                "last_n_calls": [],
            }
            return DimScanResult(empty_val, (), None)
        last = evs[-1]
        recent = evs[-10:]
        candidate = any(
            e.payload.get("tool_name", "") in _RED_LINE_CANDIDATE_TOOLS for e in recent
        )
        value = {
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
        }
        # evidence_refs 指向 recent 窗口全部源 event_id（去重保序）
        refs = tuple(dict.fromkeys(e.event_id for e in recent))
        return DimScanResult(value, refs, None)

    async def scan_latency_slo(self, project_id: str) -> DimScanResult:
        try:
            evs = await self.event_bus.read_event_stream(
                project_id=project_id, types=["latency_sample"], window_sec=60
            )
        except Exception:
            return DimScanResult(None, (), SupervisorError.IC_L1_09_UNAVAILABLE)
        if not evs:
            empty_val = {
                "slo_target_ms": _DEFAULT_LATENCY_SLO_MS,
                "actual_p95_ms": None,
                "actual_p99_ms": None,
                "compliance_rate": None,
            }
            return DimScanResult(empty_val, (), None)
        samples = sorted(int(e.payload.get("dur_ms", 0)) for e in evs)
        n = len(samples)
        p95 = samples[min(n - 1, int(0.95 * n))]
        p99 = samples[min(n - 1, int(0.99 * n))]
        compliance = sum(1 for s in samples if s <= _DEFAULT_LATENCY_SLO_MS) / n
        value = {
            "slo_target_ms": _DEFAULT_LATENCY_SLO_MS,
            "actual_p95_ms": p95,
            "actual_p99_ms": p99,
            "compliance_rate": round(compliance, 4),
        }
        refs = tuple(e.event_id for e in evs)
        return DimScanResult(value, refs, None)

    async def scan_all(self, project_id: str) -> dict[str, DimScanResult]:
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
