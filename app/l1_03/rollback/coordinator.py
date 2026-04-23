"""`RollbackCoordinator` · L2-05 主类。

接口：
- `on_wp_failed(wp_id, reason, fail_level, evidence_ref)` · L2-04 转发
- `on_wp_done_reset(wp_id)` · L2-04 成功后 reset · 幂等
- `on_deadlock_notified(project_id)` · L2-03 dispatcher 发现死锁 → IC-15 halt

实现 `RollbackCoordinatorProtocol`（WP04 定义）· 可直接注入 ProgressTracker。
"""

from __future__ import annotations

import contextlib
import threading
import uuid
from typing import Any

from app.l1_03.rollback.escalator import Escalator, RollbackRoute
from app.l1_03.rollback.failure_counter import (
    FailureCounter,
    FailureCounterState,
)
from app.l1_03.rollback.schemas import (
    AdviceOption,
    FailureCounterSnapshot,
    RollbackAdvice,
)


def _default_options() -> list[AdviceOption]:
    """默认三选一 advice（`architecture.md §8.3`）。"""
    return [AdviceOption.SPLIT_WP, AdviceOption.MODIFY_WBS, AdviceOption.MODIFY_AC]


class RollbackCoordinator:
    """WP05 主协调器 · 持 FailureCounter + Escalator + manager 引用。

    可选注入 manager → 失败到 RETRY_3 时顺带 `mark_stuck`（FAILED→STUCK 合法跃迁）。
    """

    RETRY_LIMIT: int = 2  # 连续 ≥ 3 次触发升级（counter RETRY_2 下一步即 RETRY_3）

    def __init__(
        self,
        project_id: str,
        escalator: Escalator | None = None,
        manager: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        if not project_id:
            raise ValueError("project_id 必带（PM-14）")
        self.project_id = project_id
        self.counter = FailureCounter()
        self.escalator = escalator or Escalator()
        self._manager = manager
        self._event_bus = event_bus
        self._lock = threading.RLock()

    # --- WP04 Protocol ---

    def on_wp_failed(
        self,
        wp_id: str,
        reason: str = "",
        fail_level: str = "L2",
        evidence_ref: str | None = None,
    ) -> None:
        """收到失败信号 · 推进 counter · 达 RETRY_3 触发升级。"""
        with self._lock:
            new_state = self.counter.on_failed(wp_id)
            count = self.counter.count_of(wp_id)

        if new_state in (FailureCounterState.RETRY_3, FailureCounterState.ESCALATED):
            self._escalate(
                wp_id=wp_id, reason=reason, fail_level=fail_level,
                evidence_ref=evidence_ref, failure_count=count,
            )

    def on_wp_done_reset(self, wp_id: str) -> None:
        """幂等 · 清零该 wp 的连续失败计数。"""
        self.counter.on_done_reset(wp_id)

    # --- IC-15 halt 入口 ---

    def on_deadlock_notified(self, project_id: str, reason: str = "deadlock") -> None:
        """L2-03 调度器发现死锁 · 立即 IC-15 request_hard_halt。"""
        if project_id != self.project_id:
            return  # PM-14
        self.escalator.request_hard_halt(project_id, f"L2-05 deadlock · {reason}")
        self._emit_hard_halt(project_id, reason)

    # --- 查询 ---

    def snapshot(self, wp_id: str) -> FailureCounterSnapshot:
        return FailureCounterSnapshot(
            wp_id=wp_id,
            state=str(self.counter.state_of(wp_id)),
            consecutive_failures=self.counter.count_of(wp_id),
        )

    # --- internal ---

    def _escalate(
        self,
        wp_id: str,
        reason: str,
        fail_level: str,
        evidence_ref: str | None,
        failure_count: int,
    ) -> None:
        advice = RollbackAdvice(
            wp_id=wp_id,
            project_id=self.project_id,
            failure_count=failure_count,
            options=_default_options(),
            evidence_refs=[evidence_ref] if evidence_ref else [],
            reason=f"[{fail_level}] {reason}",
        )
        route = RollbackRoute(
            route_id=f"route-{uuid.uuid4().hex[:12]}",
            project_id=self.project_id,
            advice=advice,
            target_l1="L1-04",
        )
        self.escalator.push_rollback_route(route)

        # manager.mark_stuck（FAILED→STUCK）· 可选 · 失败不阻塞升级
        if self._manager is not None:
            with contextlib.suppress(Exception):
                self._manager.mark_stuck(wp_id)

        self._emit_advice_issued(advice)

    def _emit_advice_issued(self, advice: RollbackAdvice) -> None:
        if self._event_bus is None:
            return
        self._event_bus.append(
            event_type="L1-03:rollback_advice_issued",
            content={
                "wp_id": advice.wp_id,
                "failure_count": advice.failure_count,
                "options": [str(o) for o in advice.options],
                "evidence_refs": list(advice.evidence_refs),
                "reason": advice.reason,
            },
            project_id=self.project_id,
        )

    def _emit_hard_halt(self, project_id: str, reason: str) -> None:
        if self._event_bus is None:
            return
        self._event_bus.append(
            event_type="L1-03:request_hard_halt",
            content={"reason": reason, "source": "L2-05 deadlock"},
            project_id=project_id,
        )
