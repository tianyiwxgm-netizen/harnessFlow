"""HRL-03 · 可追溯率 < 100% detector。

context['traceability_report']:
- dict({"total": int, "traceable": int})
- rate = traceable / total · rate < 1.0 → 命中
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
class TraceabilityDetector:
    name: str = "traceability"
    red_line_id: RedLineId = RedLineId.HRL_03_TRACEABILITY

    async def detect(
        self, project_id: str, context: dict[str, Any]
    ) -> DetectionResult:
        start_us = time.perf_counter_ns() // 1000
        report = context.get("traceability_report") or {}
        total = int(report.get("total") or 0)
        traceable = int(report.get("traceable") or 0)
        untraceable_refs = list(report.get("untraceable_refs") or [])

        end_us = time.perf_counter_ns() // 1000
        latency_us = max(0, end_us - start_us)

        # total=0 视为无数据（非命中）· 避免空 report 触发误报
        if total == 0:
            return DetectionResult(
                detector_name=self.name,
                red_line_id=self.red_line_id,
                hit=None,
                latency_us=latency_us,
            )

        rate = traceable / total
        if rate >= 1.0:
            return DetectionResult(
                detector_name=self.name,
                red_line_id=self.red_line_id,
                hit=None,
                latency_us=latency_us,
            )

        # rate < 1.0 即命中
        obs_refs: tuple[str, ...] = tuple(
            untraceable_refs[:10] if untraceable_refs else [f"trace-rate-{rate:.3f}"]
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
                    "total": total,
                    "traceable": traceable,
                    "rate": rate,
                },
            ),
            reason=(
                f"HRL-03: traceability rate {rate:.3%} < 100% "
                f"({traceable}/{total})"
            ),
            hit_id=f"hit-{uuid.uuid4().hex[:12]}",
        )
        return DetectionResult(
            detector_name=self.name,
            red_line_id=self.red_line_id,
            hit=hit,
            latency_us=latency_us,
        )
