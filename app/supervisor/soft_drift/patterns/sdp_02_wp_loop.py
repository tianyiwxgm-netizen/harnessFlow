"""SDP-02 · WP 循环反复 · fail_count ≥ 3 in window。"""
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
class WpLoopPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_02_WP_LOOP
    threshold: int = 3

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.wp_fail_max < self.threshold:
            return None
        tick_seqs = tuple(
            t.tick_seq
            for t in window.ticks
            if (t.wp_fail_count or 0) >= self.threshold
        )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-02: WP 循环反复 · max_fail_count={stats.wp_fail_max} "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
