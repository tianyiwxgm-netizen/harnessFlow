"""FailureCounter · per wp_id 失败计数 + 5 态机 · DONE 时 reset。

5 态机：
    ACTIVE → (fail) → RETRY_1 → (fail) → RETRY_2 → (fail) → RETRY_3=ESCALATED
    任何状态 → (DONE) → ACTIVE（count=0）

record_fail 返回 EscalationDecision：
- 第 3 次 fail · new_state=ESCALATED · should_escalate=true
- 第 ≥4 次 fail · 已 ESCALATED · dedup_hit=true · should_escalate=false（不重复发 IC-14）
  参考 Dev-ε `RollbackCoordinator._escalated_wps` · 425a30a pattern
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.supervisor.escalator.schemas import (
    EscalationDecision,
    EscalationState,
    WpDoneEvent,
    WpFailEvent,
)


@dataclass
class FailureCounter:
    """per wp_id 的计数器 · 线程不安全（单 session）· 多 wp 独立。"""

    _fail_counts: dict[str, int] = field(default_factory=dict)
    _states: dict[str, EscalationState] = field(default_factory=dict)
    _escalated_wps: set[str] = field(default_factory=set)  # dedup set

    def fail_count_for(self, wp_id: str) -> int:
        return self._fail_counts.get(wp_id, 0)

    def state_for(self, wp_id: str) -> EscalationState:
        return self._states.get(wp_id, EscalationState.ACTIVE)

    def record_fail(self, event: WpFailEvent) -> EscalationDecision:
        wp_id = event.wp_id
        prev_state = self.state_for(wp_id)

        # dedup · 已升级过 · 不再推进 · 不再触发 IC-14
        if wp_id in self._escalated_wps:
            return EscalationDecision(
                wp_id=wp_id,
                previous_state=prev_state,
                new_state=EscalationState.ESCALATED,
                should_escalate=False,
                fail_count=self.fail_count_for(wp_id),
                dedup_hit=True,
            )

        new_count = self.fail_count_for(wp_id) + 1
        self._fail_counts[wp_id] = new_count

        # 状态机推进（5 态 · ACTIVE→RETRY_1→RETRY_2→RETRY_3→ESCALATED）
        # 第 3 次 fail = RETRY_3 · 同时发升级信号（避免等第 4 次 · 仲裁要求同级连 ≥3）
        if new_count == 1:
            new_state = EscalationState.RETRY_1
            should_escalate = False
        elif new_count == 2:
            new_state = EscalationState.RETRY_2
            should_escalate = False
        elif new_count == 3:
            # 第 3 次 fail · 进入 RETRY_3 · 同时升级（触发 IC-14 UPGRADE）
            new_state = EscalationState.RETRY_3
            should_escalate = True
            self._escalated_wps.add(wp_id)
        else:
            # 理论不可达（≥4 应已走 dedup 分支）· 兜底 ESCALATED
            new_state = EscalationState.ESCALATED
            should_escalate = False

        self._states[wp_id] = new_state
        return EscalationDecision(
            wp_id=wp_id,
            previous_state=prev_state,
            new_state=new_state,
            should_escalate=should_escalate,
            fail_count=new_count,
            dedup_hit=False,
        )

    def record_done(self, event: WpDoneEvent) -> None:
        """DONE 事件 · reset counter + state + dedup set（允许再次升级）。"""
        wp_id = event.wp_id
        self._fail_counts.pop(wp_id, None)
        self._states[wp_id] = EscalationState.ACTIVE
        self._escalated_wps.discard(wp_id)
