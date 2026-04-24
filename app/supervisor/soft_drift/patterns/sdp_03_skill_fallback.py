"""SDP-03 · Skill fallback 过度 · 窗内 fallback 次数 ≥ 5。"""
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
class SkillFallbackPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_03_SKILL_FALLBACK
    threshold: int = 5

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.skill_fallback_total < self.threshold:
            return None
        tick_seqs = tuple(
            t.tick_seq
            for t in window.ticks
            if (t.skill_fallback_count or 0) > 0
        )
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-03: Skill fallback 过度 · total={stats.skill_fallback_total} "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
