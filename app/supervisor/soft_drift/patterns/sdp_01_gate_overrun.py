"""SDP-01 · Gate 过度让步 · 窗内 ≥ 3 次 TOLERATED。"""
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
class GateOverrunPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_01_GATE_OVERRUN
    threshold: int = 3

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.gate_tolerated_count < self.threshold:
            return None
        tick_seqs = tuple(
            t.tick_seq for t in window.ticks if t.gate_verdict == "TOLERATED"
        )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-01: Gate 过度让步 · {stats.gate_tolerated_count} 次 TOLERATED "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
