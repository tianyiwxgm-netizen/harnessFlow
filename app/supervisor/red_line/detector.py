"""L2-03 · 总调度 RedLineDetector · 5 detector 并发 · P99 ≤ 500ms。

流程：
1. asyncio.gather(5 detector)
2. 收集 DetectionResult[] · 含命中 / latency
3. 命中 → 调用 halt_requester（IC-15）
4. 返回 ScanReport（命中数 / 各 detector 延迟 / 总延迟）
5. IC-09 append `L1-07:redline_scan_completed`

命中 halt 动作由 subagent 注入 · 本模块只组装并 invoke。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import HaltRequester
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltAck,
    RequestHardHaltCommand,
)
from app.supervisor.red_line.audit_broken import AuditChainBrokenDetector
from app.supervisor.red_line.halt_miss import HaltLatencyMissDetector
from app.supervisor.red_line.panic_miss import PanicLatencyMissDetector
from app.supervisor.red_line.pm14_violator import PM14Violator
from app.supervisor.red_line.schemas import (
    DetectionResult,
    RedLineHit,
    RedLineId,
)
from app.supervisor.red_line.traceability import TraceabilityDetector


class Detector(Protocol):
    name: str
    red_line_id: RedLineId

    async def detect(
        self, project_id: str, context: dict[str, Any]
    ) -> DetectionResult: ...


@dataclass(frozen=True)
class ScanReport:
    """一次完整 5-detector 扫描报告。"""

    project_id: str
    results: tuple[DetectionResult, ...]
    total_latency_us: int
    hit_count: int
    halt_acks: tuple[RequestHardHaltAck, ...]
    scan_id: str


@dataclass
class RedLineDetector:
    """L2-03 主入口 · 并发 5 detector + 命中即 halt。"""

    session_pid: str
    halt_requester: HaltRequester
    event_bus: EventBusStub
    detectors: list[Detector] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.detectors:
            self.detectors = [
                PM14Violator(),
                AuditChainBrokenDetector(),
                TraceabilityDetector(),
                PanicLatencyMissDetector(),
                HaltLatencyMissDetector(),
            ]

    async def scan(
        self, project_id: str, context: dict[str, Any]
    ) -> ScanReport:
        """并发跑 5 detector · 命中即 halt · 返回完整 report。"""
        if project_id != self.session_pid:
            raise ValueError(
                f"E_REDLINE_NO_PROJECT_ID: cross-project scan forbidden "
                f"{project_id} != {self.session_pid}"
            )

        start_ns = time.perf_counter_ns()
        results: list[DetectionResult] = list(
            await asyncio.gather(
                *(d.detect(project_id, context) for d in self.detectors)
            )
        )
        end_ns = time.perf_counter_ns()
        total_latency_us = max(0, (end_ns - start_ns) // 1000)

        hits: list[RedLineHit] = [r.hit for r in results if r.hit is not None]

        # 并发 halt（每命中一条 → 一个 IC-15 request_hard_halt）
        # 注意幂等 · halt_requester 内部按 red_line_id dedup · 同一 scan 内多 hit 不同 id
        halt_acks: list[RequestHardHaltAck] = []
        if hits:
            halt_tasks = [self._halt_for_hit(h) for h in hits]
            raw_acks = await asyncio.gather(*halt_tasks, return_exceptions=True)
            for ack in raw_acks:
                if isinstance(ack, RequestHardHaltAck):
                    halt_acks.append(ack)

        scan_id = f"scan-{uuid.uuid4().hex[:12]}"

        # IC-09 审计 scan 完成
        await self.event_bus.append_event(
            project_id=project_id,
            type="L1-07:redline_scan_completed",
            payload={
                "scan_id": scan_id,
                "detector_count": len(self.detectors),
                "hit_count": len(hits),
                "hits": [h.red_line_id.value for h in hits],
                "total_latency_us": total_latency_us,
            },
        )
        if total_latency_us > 500_000:
            await self.event_bus.append_event(
                project_id=project_id,
                type="L1-07:redline_slo_violated",
                payload={
                    "scan_id": scan_id,
                    "latency_us": total_latency_us,
                    "slo_target_us": 500_000,
                    "error_code": "E_REDLINE_SLO_VIOLATION_500MS",
                },
            )

        return ScanReport(
            project_id=project_id,
            results=tuple(results),
            total_latency_us=total_latency_us,
            hit_count=len(hits),
            halt_acks=tuple(halt_acks),
            scan_id=scan_id,
        )

    async def _halt_for_hit(self, hit: RedLineHit) -> RequestHardHaltAck:
        """组装 IC-15 command · 交给 halt_requester。"""
        cmd = RequestHardHaltCommand(
            halt_id=f"halt-{uuid.uuid4().hex[:12]}",
            project_id=hit.project_id,
            red_line_id=hit.red_line_id.value,
            evidence=HardHaltEvidence(
                observation_refs=hit.evidence.observation_refs,
                confirmation_count=2,  # 硬红线二次确认（detector hit + halt_requester check）
            ),
            ts="2026-04-23T00:00:00Z",  # 不读 wall-clock · 固定符号（生产侧由时钟注入）
        )
        return await self.halt_requester.request_hard_halt(cmd)
