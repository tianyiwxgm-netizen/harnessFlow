"""SDP-04 · KB 命中率骤降 · 窗内 kb_hit_rate 平均 < 0.30。"""
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
class KbMissPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_04_KB_MISS
    threshold_rate: float = 0.30

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.kb_hit_rate_avg is None:
            return None
        if stats.kb_hit_rate_avg >= self.threshold_rate:
            return None
        tick_seqs = tuple(
            t.tick_seq
            for t in window.ticks
            if t.kb_hit_rate is not None and t.kb_hit_rate < self.threshold_rate
        )
        if not tick_seqs:
            # 平均低但无单 tick 命中下限 · 保守取全部
            tick_seqs = tuple(
                t.tick_seq for t in window.ticks if t.kb_hit_rate is not None
            )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-04: KB 命中率 avg={stats.kb_hit_rate_avg:.3f} "
                f"< threshold={self.threshold_rate}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
