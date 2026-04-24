"""SDP-07 · Verifier 连续拒绝 · streak ≥ 3。"""
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
class VerifierRejectPattern:
    pattern_id: TrapPatternId = TrapPatternId.SDP_07_VERIFIER_REJECT
    threshold: int = 3

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None:
        if stats.verifier_reject_streak < self.threshold:
            return None
        # 从最新 tick 往前收集连续 REJECT 的 tick_seq
        reject_seqs: list[int] = []
        for t in reversed(window.ticks):
            if t.verifier_verdict == "REJECT":
                reject_seqs.append(t.tick_seq)
            elif t.verifier_verdict == "PASS":
                break
        reject_seqs.reverse()
        tick_seqs = tuple(reject_seqs)
        if not tick_seqs:
            return None
        return TrapMatch(
            project_id=stats.project_id,
            pattern_id=self.pattern_id,
            reason=(
                f"SDP-07: Verifier 连续 REJECT streak={stats.verifier_reject_streak} "
                f"≥ threshold={self.threshold}"
            ),
            evidence_tick_seqs=tick_seqs,
            first_tick_seq=tick_seqs[0],
            last_tick_seq=tick_seqs[-1],
            match_id=f"sdp-{uuid.uuid4().hex[:12]}",
        )
