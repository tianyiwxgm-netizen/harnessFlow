"""SDP-08 · 状态机逆转回撤 · 相邻 tick state_seq 逆序 ≥ 2 次。"""
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
class StateReversePattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_08_STATE_REVERSE
    threshold: int = 2

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.state_reverse_count < self.threshold:
            return None
        # 找出逆序发生的 tick
        reverse_seqs: list[int] = []
        prev: str | None = None
        for t in window.ticks:
            if t.state_seq is None:
                prev = None
                continue
            if prev is not None and t.state_seq < prev:
                reverse_seqs.append(t.tick_seq)
            prev = t.state_seq
        tick_seqs = tuple(reverse_seqs)
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-08: 状态机逆转 count={stats.state_reverse_count} "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
