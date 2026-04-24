"""60-tick 滑窗聚合。

ring buffer 实现 · push Tick · 超容量丢最旧 · aggregate() 产 WindowStats。

纯内存实现 · 任何 recovery 丢窗是容忍的（软漂移非硬 SLO 项）。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from app.supervisor.soft_drift.schemas import Tick, WindowStats


@dataclass
class TickWindow:
    """60-tick 滑窗。"""

    project_id: str
    window_size: int = 60
    _ticks: Deque[Tick] = field(default_factory=deque)

    def push(self, tick: Tick) -> None:
        """入新 tick · 超容量丢最旧。"""
        if tick.project_id != self.project_id:
            raise ValueError(
                f"E_SDP_CROSS_PROJECT: {tick.project_id} != {self.project_id}"
            )
        self._ticks.append(tick)
        while len(self._ticks) > self.window_size:
            self._ticks.popleft()

    @property
    def size(self) -> int:
        return len(self._ticks)

    @property
    def ticks(self) -> list[Tick]:
        return list(self._ticks)

    def aggregate(self) -> WindowStats:
        """产 WindowStats 聚合。"""
        if not self._ticks:
            return WindowStats(
                project_id=self.project_id,
                window_size=self.window_size,
                tick_count=0,
            )
        first = self._ticks[0]
        last = self._ticks[-1]

        gate_tolerated = sum(
            1 for t in self._ticks if t.gate_verdict == "TOLERATED"
        )
        wp_fail_max = max(
            (t.wp_fail_count or 0 for t in self._ticks),
            default=0,
        )
        sk_fallback = sum(t.skill_fallback_count or 0 for t in self._ticks)
        kb_rates = [
            t.kb_hit_rate for t in self._ticks if t.kb_hit_rate is not None
        ]
        kb_avg: float | None = (
            sum(kb_rates) / len(kb_rates) if kb_rates else None
        )
        audit_p95_max = max(
            (t.audit_p95_ms or 0 for t in self._ticks),
            default=0,
        )
        ui_panic = sum(t.ui_panic_count or 0 for t in self._ticks)
        # verifier reject 连续 streak（从最新 tick 往前数）· 遇到 PASS 即断
        reject_streak = 0
        for t in reversed(self._ticks):
            if t.verifier_verdict == "REJECT":
                reject_streak += 1
            elif t.verifier_verdict == "PASS":
                break
            # None 不算断
        # state_reverse · 相邻 tick state_seq 发生降序（比较字典序）
        reverse_count = 0
        prev: str | None = None
        for t in self._ticks:
            if t.state_seq is None:
                prev = None
                continue
            if prev is not None and t.state_seq < prev:
                reverse_count += 1
            prev = t.state_seq

        return WindowStats(
            project_id=self.project_id,
            window_size=self.window_size,
            tick_count=len(self._ticks),
            first_tick_seq=first.tick_seq,
            last_tick_seq=last.tick_seq,
            gate_tolerated_count=gate_tolerated,
            wp_fail_max=wp_fail_max,
            skill_fallback_total=sk_fallback,
            kb_hit_rate_avg=kb_avg,
            audit_p95_max=audit_p95_max,
            ui_panic_total=ui_panic,
            verifier_reject_streak=reject_streak,
            state_reverse_count=reverse_count,
        )
