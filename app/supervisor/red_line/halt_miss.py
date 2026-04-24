"""HRL-05 · halt 请求未 100ms 响应 detector。

context['halt_latency_report']:
- dict({"samples_ms": list[int], "threshold_ms": 100})
- 任何 samples_ms 超 100 → 命中
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.supervisor.red_line.schemas import (
    DetectionResult,
    Evidence,
    RedLineHit,
    RedLineId,
    RedLineSeverity,
)


@dataclass
class HaltLatencyMissDetector:
    name: str = "halt_miss"
    red_line_id: RedLineId = RedLineId.HRL_05_HALT_MISS
    threshold_ms: int = 100

    async def detect(
        self, project_id: str, context: dict[str, Any]
    ) -> DetectionResult:
        start_us = time.perf_counter_ns() // 1000
        report = context.get("halt_latency_report") or {}
        samples: list[int] = [int(x) for x in (report.get("samples_ms") or [])]
        thr = int(report.get("threshold_ms") or self.threshold_ms)
        violations = [s for s in samples if s > thr]

        end_us = time.perf_counter_ns() // 1000
        latency_us = max(0, end_us - start_us)

        if not violations:
            return DetectionResult(
                detector_name=self.name,
                red_line_id=self.red_line_id,
                hit=None,
                latency_us=latency_us,
            )

        max_lat = max(violations)
        refs = report.get("sample_refs") or []
        obs_refs: tuple[str, ...] = tuple(refs[:10]) if refs else (
            f"halt-latency-max-{max_lat}ms",
        )
        hit = RedLineHit(
            red_line_id=self.red_line_id,
            project_id=project_id,
            severity=RedLineSeverity.CRITICAL,
            evidence=Evidence(
                observation_refs=obs_refs,
                detector_name=self.name,
                detected_at_ms=int(time.time() * 1000),
                extra={
                    "violations": len(violations),
                    "total": len(samples),
                    "max_ms": max_lat,
                    "threshold_ms": thr,
                },
            ),
            reason=(
                f"HRL-05: halt {len(violations)}/{len(samples)} samples > {thr}ms "
                f"(max {max_lat}ms)"
            ),
            hit_id=f"hit-{uuid.uuid4().hex[:12]}",
        )
        return DetectionResult(
            detector_name=self.name,
            red_line_id=self.red_line_id,
            hit=hit,
            latency_us=latency_us,
        )
