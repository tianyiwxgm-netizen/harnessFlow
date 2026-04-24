"""HRL-01 · PM-14 违规 detector · 检查事件流有无 pid 缺失 / 跨 pid 污染。

输入（SupervisorContext）:
- project_id: 当前 session pid
- recent_events: list[Event]（L1-09 event_bus 最近窗口）· Event.project_id

命中条件（任一）：
1. 任一 event.project_id 为空字符串 / None
2. 任一 event.project_id != 当前 project_id（跨 pid 污染）
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
class PM14Violator:
    """HRL-01 detector · 纯函数执行 · 无 I/O · 从 context 读。"""

    name: str = "pm14_violator"
    red_line_id: RedLineId = RedLineId.HRL_01_PM14_VIOLATION

    async def detect(
        self, project_id: str, context: dict[str, Any]
    ) -> DetectionResult:
        """扫 context['recent_events']（list[Event-like dict]）查 pid 违规。"""
        start_us = time.perf_counter_ns() // 1000
        events = context.get("recent_events", []) or []
        offenders: list[str] = []
        for ev in events:
            ev_pid = getattr(ev, "project_id", None) if not isinstance(ev, dict) else ev.get("project_id")
            ev_id = getattr(ev, "event_id", None) if not isinstance(ev, dict) else ev.get("event_id", "ev-unknown")
            if not ev_pid or not str(ev_pid).strip():
                offenders.append(str(ev_id))
                continue
            if str(ev_pid) != str(project_id):
                offenders.append(str(ev_id))

        end_us = time.perf_counter_ns() // 1000
        latency_us = max(0, end_us - start_us)

        if not offenders:
            return DetectionResult(
                detector_name=self.name,
                red_line_id=self.red_line_id,
                hit=None,
                latency_us=latency_us,
            )

        hit = RedLineHit(
            red_line_id=self.red_line_id,
            project_id=project_id,
            severity=RedLineSeverity.CRITICAL,
            evidence=Evidence(
                observation_refs=tuple(offenders[:10]),
                detector_name=self.name,
                detected_at_ms=int(time.time() * 1000),
                extra={"offender_count": len(offenders)},
            ),
            reason=(
                f"HRL-01: {len(offenders)} event(s) violate PM-14 "
                f"(missing pid / cross-pid)"
            ),
            hit_id=f"hit-{uuid.uuid4().hex[:12]}",
        )
        return DetectionResult(
            detector_name=self.name,
            red_line_id=self.red_line_id,
            hit=hit,
            latency_us=latency_us,
        )
