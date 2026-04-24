"""Soft-drift 主匹配引擎。

流程：
1. TickWindow.push(tick)（滑窗维护）
2. window.aggregate() → WindowStats
3. 8 pattern 并行 check() → 命中
4. 命中 → 调 suggestion_pusher（IC-13）level=WARN
5. IC-09 append `L1-07:soft_drift_matched`

dedup：同 project · 同 pattern_id · 同 last_tick_seq 视为已发（避免重复 IC-13）。
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.schemas import (
    PushSuggestionAck,
    PushSuggestionCommand,
    SuggestionLevel,
    SuggestionPriority,
)
from app.supervisor.event_sender.suggestion_pusher import SuggestionPusher
from app.supervisor.soft_drift.patterns.sdp_01_gate_overrun import (
    GateOverrunPattern,
)
from app.supervisor.soft_drift.patterns.sdp_02_wp_loop import WpLoopPattern
from app.supervisor.soft_drift.patterns.sdp_03_skill_fallback import (
    SkillFallbackPattern,
)
from app.supervisor.soft_drift.patterns.sdp_04_kb_miss import KbMissPattern
from app.supervisor.soft_drift.patterns.sdp_05_audit_tail import AuditTailPattern
from app.supervisor.soft_drift.patterns.sdp_06_ui_panic import UiPanicPattern
from app.supervisor.soft_drift.patterns.sdp_07_verifier_reject import (
    VerifierRejectPattern,
)
from app.supervisor.soft_drift.patterns.sdp_08_state_reverse import (
    StateReversePattern,
)
from app.supervisor.soft_drift.schemas import (
    Tick,
    TrapMatch,
    TrapPatternId,
    WindowStats,
)
from app.supervisor.soft_drift.window_stats import TickWindow


class Pattern(Protocol):
    pattern_id: TrapPatternId

    def check(
        self, window: TickWindow, stats: WindowStats
    ) -> TrapMatch | None: ...


@dataclass(frozen=True)
class MatchReport:
    project_id: str
    matches: tuple[TrapMatch, ...]
    suggestions_pushed: tuple[PushSuggestionAck, ...]
    stats: WindowStats
    run_id: str


@dataclass
class SoftDriftMatcher:
    """L2-05 主匹配引擎。"""

    session_pid: str
    suggestion_pusher: SuggestionPusher
    event_bus: EventBusStub
    window: TickWindow = field(default=None)  # type: ignore[assignment]
    patterns: list[Pattern] = field(default_factory=list)
    # dedup: (pattern_id, last_tick_seq) 已发过 → 跳
    _dedup: set[tuple[TrapPatternId, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.window is None:
            self.window = TickWindow(project_id=self.session_pid)
        if not self.patterns:
            self.patterns = [
                GateOverrunPattern(),
                WpLoopPattern(),
                SkillFallbackPattern(),
                KbMissPattern(),
                AuditTailPattern(),
                UiPanicPattern(),
                VerifierRejectPattern(),
                StateReversePattern(),
            ]

    async def feed(self, tick: Tick) -> MatchReport:
        """入新 tick · 跑 8 pattern · 命中 → IC-13 WARN。"""
        if tick.project_id != self.session_pid:
            raise ValueError(
                f"E_SDP_CROSS_PROJECT: {tick.project_id} != {self.session_pid}"
            )
        self.window.push(tick)
        stats = self.window.aggregate()

        matches: list[TrapMatch] = []
        for pattern in self.patterns:
            m = pattern.check(self.window, stats)
            if m is None:
                continue
            key = (m.pattern_id, m.last_tick_seq)
            if key in self._dedup:
                continue
            self._dedup.add(key)
            matches.append(m)

        # 并发推 IC-13 WARN
        acks: list[PushSuggestionAck] = []
        if matches:
            ack_coros = [self._push_warn(m) for m in matches]
            raw_acks = await asyncio.gather(*ack_coros, return_exceptions=True)
            for ack in raw_acks:
                if isinstance(ack, PushSuggestionAck):
                    acks.append(ack)

        run_id = f"sdp-run-{uuid.uuid4().hex[:12]}"

        # IC-09 审计
        await self.event_bus.append_event(
            project_id=self.session_pid,
            type="L1-07:soft_drift_scanned",
            payload={
                "run_id": run_id,
                "tick_seq": tick.tick_seq,
                "match_count": len(matches),
                "matched_patterns": [m.pattern_id.value for m in matches],
                "window_size": stats.tick_count,
            },
        )
        return MatchReport(
            project_id=self.session_pid,
            matches=tuple(matches),
            suggestions_pushed=tuple(acks),
            stats=stats,
            run_id=run_id,
        )

    async def _push_warn(self, match: TrapMatch) -> PushSuggestionAck:
        """组装 IC-13 WARN suggestion · 交 SuggestionPusher。"""
        content = (
            f"[SDP {match.pattern_id.value}] {match.reason} · "
            f"ticks={match.first_tick_seq}..{match.last_tick_seq}"
        )
        cmd = PushSuggestionCommand(
            suggestion_id=f"sugg-{match.match_id}",
            project_id=match.project_id,
            level=SuggestionLevel.WARN,
            content=content,
            observation_refs=tuple(
                f"tick-{s}" for s in match.evidence_tick_seqs[:10]
            ),
            priority=SuggestionPriority.P1,
            ts=datetime.now(UTC).isoformat(),
        )
        return await self.suggestion_pusher.push_suggestion(cmd)
