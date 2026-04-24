"""EscalationLogic · 订阅 wp_failed / wp_done · 5 态机 → IC-14 push_rollback_route。

**主会话仲裁**：同级连 ≥ 3 failed 触发升级 · 实际动作走 IC-14（UPGRADE_TO_L1-01 target_stage）·
非 IC-13 L4。参考 Dev-ε RollbackCoordinator._escalated_wps 的 dedup pattern。

逻辑：
1. on_wp_failed(event) → counter.record_fail(event)
2. decision.should_escalate=true → 组装 PushRollbackRouteCommand 调 rollback_pusher
   - verdict = WpFailLevel 映射（L1→FAIL_L1 / L2→FAIL_L2 / L3→FAIL_L3 / L4→FAIL_L4）
   - target_stage = UPGRADE_TO_L1-01（升级语义）
   - level_count = 3（已连续 3 fail）
3. on_wp_done(event) → counter.record_done · 允许下次重新升级

dedup：counter 层已做 set 标记 · 本层依据 decision.should_escalate 决策 · 第 2 次升级不会发起。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.supervisor.escalator.counter import FailureCounter
from app.supervisor.escalator.schemas import WpDoneEvent, WpFailEvent, WpFailLevel
from app.supervisor.event_sender.rollback_pusher import RollbackPusher
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)


_LEVEL_TO_VERDICT = {
    WpFailLevel.L1: FailVerdict.FAIL_L1,
    WpFailLevel.L2: FailVerdict.FAIL_L2,
    WpFailLevel.L3: FailVerdict.FAIL_L3,
    WpFailLevel.L4: FailVerdict.FAIL_L4,
}


@dataclass
class EscalationLogic:
    """死循环升级编排 · 串起 FailureCounter + RollbackPusher(IC-14)。"""

    session_pid: str
    counter: FailureCounter
    rollback_pusher: RollbackPusher

    async def on_wp_failed(
        self, event: WpFailEvent
    ) -> PushRollbackRouteAck | None:
        """输入：WP 失败事件 · 输出：若触发升级 · 返回 IC-14 ack · 否则 None。"""
        if event.project_id != self.session_pid:
            # 跨 project 直接丢弃（非本 session 负责）
            return None

        decision = self.counter.record_fail(event)

        if not decision.should_escalate:
            return None

        # 组装 IC-14 push_rollback_route
        verdict = _LEVEL_TO_VERDICT[event.verdict_level]
        route_id = f"route-esc-{uuid.uuid4().hex[:12]}"
        cmd = PushRollbackRouteCommand(
            route_id=route_id,
            project_id=event.project_id,
            wp_id=event.wp_id,
            verdict=verdict,
            target_stage=TargetStage.UPGRADE_TO_L1_01,
            level_count=decision.fail_count,
            evidence=RouteEvidence(verifier_report_id=event.verifier_report_id),
            ts=event.ts,
        )
        ack = await self.rollback_pusher.push_rollback_route(cmd)
        return ack

    def on_wp_done(self, event: WpDoneEvent) -> None:
        """WP 成功 · counter reset · dedup set 清空 · 允许下次重新升级。"""
        if event.project_id != self.session_pid:
            return
        self.counter.record_done(event)
