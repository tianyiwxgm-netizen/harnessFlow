"""L2-03 调度主流程 · IC-02 入口。

算法（`architecture.md §6.2`）：
    snapshot = manager.read_snapshot()
    if no READY/BLOCKED/FAILED remain and all DONE: return (null, all_done)
    candidates = filter READY AND deps_met AND wp_id not in exclude
    if not candidates:
        if no READY/RUNNING left: notify deadlock → return (null, deadlock)
        return (null, awaiting_deps)
    if at concurrency cap: return (null, concurrency_cap)
    ranked = prioritize(candidates, critical_path)
    for top in ranked[:3]:
        ok = manager.transition_state(top, READY, RUNNING)
        if ok: return (top, wp_def, deps_met=True)
    return (null, lock_contention)

PM-14 硬约束：query.project_id 必须与 manager.project_id 一致，否则拒绝。
"""

from __future__ import annotations

from app.l1_03.common.errors import (
    CrossProjectDepError,
    DepsNotMetError,
    IllegalTransition,
    L103Error,
    ParallelismCapError,
    StaleStateError,
    WPNotFoundError,
)
from app.l1_03.scheduler.concurrency_guard import ConcurrencyGuard
from app.l1_03.scheduler.priority_queue import prioritize_candidates
from app.l1_03.scheduler.schemas import (
    GetNextWPQuery,
    GetNextWPResult,
    WaitingReason,
    WPDefOut,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State


class WPDispatcher:
    """IC-02 调度器 · 无状态 · 每次调用从 manager 读最新快照。"""

    MAX_LOCK_RETRIES: int = 3

    def __init__(
        self,
        manager: WBSTopologyManager,
        event_bus: object | None = None,
    ) -> None:
        self._manager = manager
        self._guard = ConcurrencyGuard(limit=manager.parallelism_limit)
        self._event_bus = event_bus

    def get_next_wp(self, query: GetNextWPQuery) -> GetNextWPResult:
        # PM-14 守卫（E_WP_CROSS_PROJECT）
        if query.project_id != self._manager.project_id:
            self._emit_noop(query, "cross_project", snapshot_size=0)
            return GetNextWPResult(
                query_id=query.query_id,
                wp_id=None,
                deps_met=False,
                waiting_reason=None,
                in_flight_wp_count=0,
                topology_version=self._manager.topology_version,
                error_code="E_WP_CROSS_PROJECT",
            )

        # 读快照
        snapshot = self._manager.read_snapshot()
        topo_layers = self._manager.topological_layers()
        total_wps = len(snapshot.wp_states)

        # all-done 判定
        if total_wps > 0 and all(
            st == State.DONE for st in snapshot.wp_states.values()
        ):
            self._emit_noop(query, WaitingReason.ALL_DONE.value, total_wps)
            return GetNextWPResult(
                query_id=query.query_id,
                wp_id=None,
                deps_met=True,
                waiting_reason=WaitingReason.ALL_DONE,
                in_flight_wp_count=snapshot.current_running_count,
                topology_version=snapshot.topology_version,
            )

        # concurrency cap
        if self._guard.at_cap(snapshot.current_running_count):
            self._emit_noop(query, WaitingReason.CONCURRENCY_CAP.value, total_wps)
            return GetNextWPResult(
                query_id=query.query_id,
                wp_id=None,
                deps_met=False,
                waiting_reason=WaitingReason.CONCURRENCY_CAP,
                in_flight_wp_count=snapshot.current_running_count,
                topology_version=snapshot.topology_version,
                error_code="E_WP_CONCURRENCY_CAP",
            )

        # 候选筛选：state=READY AND deps_met AND not excluded
        exclude = frozenset(query.exclude_wp_ids)
        candidates: list[str] = []
        for wp_id, st in snapshot.wp_states.items():
            if st != State.READY:
                continue
            if wp_id in exclude:
                continue
            if not snapshot.deps_met(wp_id):
                continue
            candidates.append(wp_id)

        if not candidates:
            # 无候选：判定 deadlock vs awaiting_deps
            # deadlock：无 READY 且无 RUNNING（没人可跑 + 没人在跑）
            any_ready = any(st == State.READY for st in snapshot.wp_states.values())
            any_running = snapshot.current_running_count > 0
            if not any_ready and not any_running:
                reason = WaitingReason.DEADLOCK
                self._emit_noop(query, reason.value, total_wps)
            else:
                reason = WaitingReason.AWAITING_DEPS
                self._emit_noop(query, reason.value, total_wps)
            return GetNextWPResult(
                query_id=query.query_id,
                wp_id=None,
                deps_met=False,
                waiting_reason=reason,
                in_flight_wp_count=snapshot.current_running_count,
                topology_version=snapshot.topology_version,
            )

        # 排序
        ranked = prioritize_candidates(
            candidates,
            snapshot,
            topo_layers=topo_layers,
            prefer_critical_path=query.prefer_critical_path,
        )

        # 试锁 top-N（至多 MAX_LOCK_RETRIES 个）· 第一个成功即返回
        alternatives: list[str] = []
        for top in ranked[: self.MAX_LOCK_RETRIES]:
            try:
                self._manager.transition_state(top, State.READY, State.RUNNING)
            except (ParallelismCapError, DepsNotMetError, IllegalTransition,
                    StaleStateError, WPNotFoundError, CrossProjectDepError):
                alternatives.append(top)
                continue
            except L103Error:
                alternatives.append(top)
                continue
            # 成功
            wp = self._manager.find_wp(top)
            assert wp is not None  # transition_state 刚成功，wp 必存在
            wp_def = WPDefOut(
                wp_id=wp.wp_id,
                project_id=wp.project_id,
                goal=wp.goal,
                dod_expr_ref=wp.dod_expr_ref,
                deps=list(wp.deps),
                effort_estimate=wp.effort_estimate,
                recommended_skills=list(wp.recommended_skills),
            )
            self._emit_dispatched(
                query, wp_id=top, candidates_size=len(candidates),
                alternatives=alternatives, ranking_reason=(
                    "critical_path" if top in snapshot.critical_path else "topo_order"
                ),
            )
            # 最新快照读一次并发位
            new_snap = self._manager.read_snapshot()
            return GetNextWPResult(
                query_id=query.query_id,
                wp_id=top,
                wp_def=wp_def,
                deps_met=True,
                waiting_reason=None,
                in_flight_wp_count=new_snap.current_running_count,
                topology_version=new_snap.topology_version,
            )

        # 所有 top 候选都被竞态拿走 · lock_contention
        self._emit_noop(query, WaitingReason.LOCK_CONTENTION.value, total_wps)
        return GetNextWPResult(
            query_id=query.query_id,
            wp_id=None,
            deps_met=False,
            waiting_reason=WaitingReason.LOCK_CONTENTION,
            in_flight_wp_count=snapshot.current_running_count,
            topology_version=snapshot.topology_version,
            error_code="E_WP_LOCK_TIMEOUT",
        )

    # --- 事件 ---

    def _emit_dispatched(
        self,
        query: GetNextWPQuery,
        wp_id: str,
        candidates_size: int,
        alternatives: list[str],
        ranking_reason: str,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.append(  # type: ignore[attr-defined]
            event_type="L1-03:wp_ready_dispatched",
            content={
                "query_id": query.query_id,
                "wp_id": wp_id,
                "requester_tick": query.requester_tick,
                "candidates_size": candidates_size,
                "alternatives": list(alternatives),
                "ranking_reason": ranking_reason,
                "deps_met": True,
            },
            project_id=self._manager.project_id,
        )

    def _emit_noop(
        self,
        query: GetNextWPQuery,
        reason: str,
        snapshot_size: int,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.append(  # type: ignore[attr-defined]
            event_type="L1-03:wp_scheduler_noop",
            content={
                "query_id": query.query_id,
                "requester_tick": query.requester_tick,
                "reason": reason,
                "snapshot_size": snapshot_size,
            },
            project_id=self._manager.project_id,
        )


def get_next_wp(
    manager: WBSTopologyManager,
    query: GetNextWPQuery,
    event_bus: object | None = None,
) -> GetNextWPResult:
    """函数式便捷入口（等价于临时构造 WPDispatcher 调 get_next_wp）。"""
    return WPDispatcher(manager=manager, event_bus=event_bus).get_next_wp(query)
