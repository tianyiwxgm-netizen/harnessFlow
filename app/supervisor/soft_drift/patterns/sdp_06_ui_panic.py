"""SDP-06 · UI panic 频发 · 24h ≥ 3（这里以窗内累计 ≥ 3 代表）。"""
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
class UiPanicPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_06_UI_PANIC
    threshold: int = 3

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.ui_panic_total < self.threshold:
            return None
        tick_seqs = tuple(
            t.tick_seq
            for t in window.ticks
            if (t.ui_panic_count or 0) > 0
        )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-06: UI panic 频发 · total={stats.ui_panic_total} "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
