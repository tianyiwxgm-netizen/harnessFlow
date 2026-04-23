"""`ProgressTracker` · L2-04 核心 · 消费事件 + 聚合指标 + 通知 L2-05。"""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol

from app.l1_03.common.errors import L103Error, StaleStateError, WPNotFoundError
from app.l1_03.progress.burndown import completion_rate, compute_burndown
from app.l1_03.progress.event_subscriber import (
    ProgressEventSubscriber,
    WPCompletionEvent,
    WPFailureEvent,
)
from app.l1_03.progress.schemas import BurndownPoint, ProgressSnapshot
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State


class RollbackCoordinatorProtocol(Protocol):
    """L2-05 将实现（WP05）。WP04 通过此接口转发失败事件。"""

    def on_wp_failed(
        self,
        wp_id: str,
        reason: str,
        fail_level: str = "L2",
        evidence_ref: str | None = None,
    ) -> None: ...

    def on_wp_done_reset(self, wp_id: str) -> None: ...


class ProgressTracker:
    """订阅 L1-04 事件 · 驱动 manager 状态跃迁 · 维护 burndown + 进度指标。

    典型用法：
        tracker = ProgressTracker(manager, event_bus, rollback_coordinator)
        tracker.register()  # 向 event_bus 订阅
        snap = tracker.progress_snapshot()  # UI/Supervisor 消费
    """

    def __init__(
        self,
        manager: WBSTopologyManager,
        event_bus: Any | None = None,
        rollback_coordinator: RollbackCoordinatorProtocol | None = None,
    ) -> None:
        self._manager = manager
        self._event_bus = event_bus
        self._rollback = rollback_coordinator
        self._lock = threading.RLock()
        self._burndown: list[BurndownPoint] = []
        self._handled_event_ids: set[str] = set()
        self._subscriber = ProgressEventSubscriber(
            on_done=self.on_wp_done,
            on_failed=self.on_wp_failed,
        )

    # --- 订阅生命周期 ---

    def register(self) -> None:
        if self._event_bus is None:
            return
        self._event_bus.subscribe(self._subscriber)

    def unregister(self) -> None:
        if self._event_bus is None:
            return
        self._event_bus.unsubscribe(self._subscriber)

    # --- 事件回调 ---

    def on_wp_done(self, event: WPCompletionEvent) -> None:
        """处理 wp_executed / wp_verified_pass 事件 · 幂等。"""
        with self._lock:
            if event.event_id and event.event_id in self._handled_event_ids:
                return  # 幂等：同 event_id 只处理一次
            if event.event_id:
                self._handled_event_ids.add(event.event_id)

        # PM-14 守卫
        if event.project_id != self._manager.project_id:
            return  # 静默忽略跨 pid 事件（不 raise · 避免 bus 订阅者崩溃）

        try:
            self._manager.transition_state(event.wp_id, State.RUNNING, State.DONE, reason="wp_done")
        except (StaleStateError, WPNotFoundError, L103Error):
            # WP 不处于 RUNNING 或不存在 · 静默（可能由回放重复触发）
            return

        # L2-05 成功后 counter reset（WP05 实现）
        if self._rollback is not None:
            self._rollback.on_wp_done_reset(event.wp_id)

        self._record_burndown()
        self._emit_metrics_updated()

    def on_wp_failed(self, event: WPFailureEvent) -> None:
        """处理 wp_failed 事件 · 幂等 · 转 L2-05。"""
        with self._lock:
            if event.event_id and event.event_id in self._handled_event_ids:
                return
            if event.event_id:
                self._handled_event_ids.add(event.event_id)

        if event.project_id != self._manager.project_id:
            return

        try:
            self._manager.transition_state(event.wp_id, State.RUNNING, State.FAILED, reason="wp_failed")
        except (StaleStateError, WPNotFoundError, L103Error):
            return

        if self._rollback is not None:
            self._rollback.on_wp_failed(
                wp_id=event.wp_id,
                reason=event.reason_summary,
                fail_level=event.fail_level,
                evidence_ref=event.failure_artifacts_ref,
            )

        self._record_burndown()
        self._emit_metrics_updated()

    # --- 聚合指标 ---

    def progress_snapshot(self) -> ProgressSnapshot:
        """合成 ProgressSnapshot。不可变 · 外部消费。"""
        with self._lock:
            topo = self._manager.topology
            if topo is None:
                return ProgressSnapshot(
                    project_id=self._manager.project_id,
                    topology_version=self._manager.topology_version,
                    total_effort=0.0,
                    done_effort=0.0,
                    remaining_effort=0.0,
                    completion_rate=0.0,
                )
            total, done = compute_burndown(topo.wp_list)
            by_state: dict[State, list[str]] = {s: [] for s in State}
            for w in topo.wp_list:
                by_state[w.state].append(w.wp_id)
            return ProgressSnapshot(
                project_id=topo.project_id,
                topology_version=self._manager.topology_version,
                total_effort=total,
                done_effort=done,
                remaining_effort=max(0.0, total - done),
                completion_rate=completion_rate(total, done),
                done_wps=by_state[State.DONE],
                failed_wps=by_state[State.FAILED],
                running_wps=by_state[State.RUNNING],
                ready_wps=by_state[State.READY],
                blocked_wps=by_state[State.BLOCKED],
                stuck_wps=by_state[State.STUCK],
                burndown_series=list(self._burndown),
            )

    # --- internal ---

    def _record_burndown(self) -> None:
        with self._lock:
            topo = self._manager.topology
            if topo is None:
                return
            total, done = compute_burndown(topo.wp_list)
            self._burndown.append(
                BurndownPoint(
                    ts=time.time(),
                    remaining_effort=max(0.0, total - done),
                    done_wp_count=sum(1 for w in topo.wp_list if w.state == State.DONE),
                )
            )

    def _emit_metrics_updated(self) -> None:
        if self._event_bus is None:
            return
        snap = self.progress_snapshot()
        self._event_bus.append(
            event_type="L1-03:progress_metrics_updated",
            content={
                "completion_rate": snap.completion_rate,
                "remaining_effort": snap.remaining_effort,
                "done_wps": list(snap.done_wps),
                "running_wps": list(snap.running_wps),
                "total_effort": snap.total_effort,
                "topology_version": snap.topology_version,
            },
            project_id=self._manager.project_id,
        )
