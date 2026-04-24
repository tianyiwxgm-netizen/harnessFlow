"""SDP-05 · Audit 写入 P95 > 20ms。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.supervisor.soft_drift.schemas import (
    TrapMatch,
    TrapPatternId,
    WindowStats,
)
from app.supervisor.soft_drift.window_stats import TickWindow


@dataclass
class AuditTailPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_05_AUDIT_TAIL
    threshold_ms: int = 20

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.audit_p95_max <= self.threshold_ms:
            return None
        tick_seqs = tuple(
            t.tick_seq
            for t in window.ticks
            if (t.audit_p95_ms or 0) > self.threshold_ms
        )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-05: Audit P95 max={stats.audit_p95_max}ms "
                f"> threshold={self.threshold_ms}ms"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
