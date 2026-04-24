"""HRL-02 · 审计链破损 detector · hash chain 断链检测。

context['audit_chain_report']:
- dict({"hash_broken": bool, "missing_events": list[str], "broken_at": str|None})
- 若 hash_broken=True 或 missing_events 非空 → 命中
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
class AuditChainBrokenDetector:
    name: str = "audit_broken"
    red_line_id: RedLineId = RedLineId.HRL_02_AUDIT_BROKEN

    async def detect(
        self, project_id: str, context: dict[str, Any]
    ) -> DetectionResult:
        start_us = time.perf_counter_ns() // 1000
        report = context.get("audit_chain_report") or {}
        hash_broken = bool(report.get("hash_broken"))
        missing = list(report.get("missing_events") or [])
        broken_at = report.get("broken_at")

        end_us = time.perf_counter_ns() // 1000
        latency_us = max(0, end_us - start_us)

        if not hash_broken and not missing:
            return DetectionResult(
                detector_name=self.name,
                red_line_id=self.red_line_id,
                hit=None,
                latency_us=latency_us,
            )

        # 证据 refs · 从 missing_events + broken_at 派生
        obs_refs: tuple[str, ...] = tuple(
            missing[:10] if missing else [str(broken_at or "chain-integrity-fail")]
        )
        if not obs_refs:
            obs_refs = ("audit-chain-broken",)

        hit = RedLineHit(
            red_line_id=self.red_line_id,
            project_id=project_id,
            severity=RedLineSeverity.CRITICAL,
            evidence=Evidence(
                observation_refs=obs_refs,
                detector_name=self.name,
                detected_at_ms=int(time.time() * 1000),
                extra={
                    "hash_broken": hash_broken,
                    "missing_count": len(missing),
                    "broken_at": broken_at,
                },
            ),
            reason=(
                f"HRL-02: hash_chain broken "
                f"(hash_broken={hash_broken}, missing={len(missing)})"
            ),
            hit_id=f"hit-{uuid.uuid4().hex[:12]}",
        )
        return DetectionResult(
            detector_name=self.name,
            red_line_id=self.red_line_id,
            hit=hit,
            latency_us=latency_us,
        )
