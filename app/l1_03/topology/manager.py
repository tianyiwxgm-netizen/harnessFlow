"""`WBSTopologyManager` · L2-02 聚合根实现。

职责（`architecture.md §5.2`）：
- 装图 + 7 不变量强制（I-1 ~ I-7）
- 状态跃迁合法性守护（LEGAL_TRANSITIONS · in_flight_count · stale state）
- 只读视图导出（snapshot / readonly_view）
- mark_stuck（L2-05 调）
- 版本号每次写操作递增（topology_version）

线程安全：`threading.RLock` 包所有写方法。
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

import networkx as nx

from app.l1_03.common.errors import (
    CrossProjectDepError,
    DepsNotMetError,
    IncompleteWPError,
    ParallelismCapError,
    PM14MismatchError,
    StaleStateError,
    WPNotFoundError,
)
from app.l1_03.topology.dag import (
    assert_acyclic,
    build_digraph,
    compute_critical_path,
    descendants,
    topological_generations,
)
from app.l1_03.topology.schemas import (
    DAGEdge,
    WBSTopology,
    WorkPackage,
)
from app.l1_03.topology.snapshot import TopologySnapshot, read_snapshot
from app.l1_03.topology.state_machine import (
    State,
    assert_transition,
)

_REQUIRED_WP_FIELDS = ("goal", "dod_expr_ref", "deps", "effort_estimate")


def _new_topology_id() -> str:
    return f"topo-{uuid.uuid4().hex[:12]}"


def _new_version() -> str:
    return f"v-{uuid.uuid4().hex[:12]}"


class WBSTopologyManager:
    """聚合根 · 单 project 内 WBSTopology 的唯一真值源。

    典型生命周期：
        manager = WBSTopologyManager(project_id="pid-alpha")
        manager.load_topology(draft)                 # 装图
        snap = manager.read_snapshot()               # 只读
        manager.transition_state(wp_id, READY, RUNNING)
        manager.mark_stuck(wp_id)
    """

    def __init__(
        self,
        project_id: str,
        parallelism_limit: int = 2,
        event_bus: Any | None = None,
    ) -> None:
        if not project_id:
            raise ValueError("project_id 必带（PM-14）")
        self.project_id = project_id
        self.parallelism_limit = parallelism_limit
        self._topology: WBSTopology | None = None
        self._g: nx.DiGraph | None = None
        self._lock = threading.RLock()
        self._version: str = ""
        # IC-L2-08 → IC-09 · 状态跃迁 / 装图完成时发 `L1-03:wp_state_changed` / `L1-03:wbs_decomposed`
        # event_bus 是 duck-typed：只要有 `append(event_type, content, project_id) -> dict` 即可
        self._event_bus = event_bus

    # ----- 装图 -----

    def load_topology(
        self,
        wp_list: list[WorkPackage] | list[dict[str, Any]],
        dag_edges: list[DAGEdge] | list[dict[str, str]] | None = None,
    ) -> WBSTopology:
        """装图 · 7 不变量全过才返回 · 任一不过整体拒绝。"""
        dag_edges = dag_edges or []
        wps = [WorkPackage.model_validate(w) if not isinstance(w, WorkPackage) else w for w in wp_list]
        edges = [
            DAGEdge.model_validate(e) if not isinstance(e, DAGEdge) else e
            for e in dag_edges
        ]

        # I-5 · 4 要素完整性（pydantic 已拦 `min_length=1` · 这里二次 assert）
        for wp in wps:
            missing = [f for f in _REQUIRED_WP_FIELDS if not _field_nonempty(wp, f)]
            if missing:
                raise IncompleteWPError(wp_id=wp.wp_id, missing_fields=missing)

        # I-2 · PM-14 归属闭包
        for wp in wps:
            if wp.project_id != self.project_id:
                raise PM14MismatchError(
                    wp_id=wp.wp_id,
                    expected_pid=self.project_id,
                    got_pid=wp.project_id,
                )

        # 悬空依赖（`set(deps) ⊆ set(wp_ids)`）
        all_ids = {w.wp_id for w in wps}
        for wp in wps:
            missing_deps = [d for d in wp.deps if d not in all_ids]
            if missing_deps:
                from app.l1_03.common.errors import DanglingDepsError
                raise DanglingDepsError(wp_id=wp.wp_id, missing_deps=missing_deps)

        # 跨 project deps（edges 端点 project_id 不同也算）
        id_to_pid = {w.wp_id: w.project_id for w in wps}
        for e in edges:
            for end in (e.from_wp_id, e.to_wp_id):
                pid = id_to_pid.get(end)
                if pid is not None and pid != self.project_id:
                    raise CrossProjectDepError(
                        wp_id=end,
                        expected_pid=self.project_id,
                        got_pid=pid,
                    )

        # I-1 · DAG 无环（build + check）
        g = build_digraph(wps, edges)
        assert_acyclic(g)

        # critical_path（I-7 依赖事件回放时也会重算）
        cp_ids = compute_critical_path(g)
        from app.l1_03.topology.schemas import CriticalPath
        cp = CriticalPath(wp_ids=cp_ids)

        topo = WBSTopology(
            project_id=self.project_id,
            topology_id=_new_topology_id(),
            wp_list=list(wps),
            dag_edges=list(edges),
            critical_path=cp,
            parallelism_limit=self.parallelism_limit,
            current_running_count=0,
        )

        with self._lock:
            self._topology = topo
            self._g = g
            self._version = _new_version()
        self._emit(
            "L1-03:wbs_decomposed",
            {
                "topology_id": topo.topology_id,
                "topology_version": self._version,
                "wp_count": len(topo.wp_list),
                "critical_path_ids": list(topo.critical_path.wp_ids),
            },
        )
        return topo

    # ----- 跃迁 -----

    def transition_state(
        self,
        wp_id: str,
        from_state: State,
        to_state: State,
        reason: str = "",
    ) -> None:
        """WP 状态跃迁 · 四层守护：LEGAL / stale / parallelism / deps_met。

        - 非法跃迁 → `IllegalTransition`（E_L103_L202_303）
        - stale（当前实际 state != from_state）→ `StaleStateError`（E_L103_L202_304）
        - 并发超限（READY→RUNNING）→ `ParallelismCapError`（E_L103_L202_301）
        - deps 未 DONE（READY→RUNNING）→ `DepsNotMetError`（E_L103_L202_302）
        """
        assert_transition(from_state, to_state, wp_id)  # 1
        with self._lock:
            topo = self._require_loaded()
            wp = self._find_wp_unlocked(wp_id)
            if wp.state != from_state:  # 2
                raise StaleStateError(
                    wp_id=wp_id,
                    expected_from=str(from_state),
                    actual=str(wp.state),
                )
            if from_state == State.READY and to_state == State.RUNNING:
                # 3 parallelism
                if topo.current_running_count >= topo.parallelism_limit:
                    raise ParallelismCapError(
                        limit=topo.parallelism_limit,
                        running=topo.current_running_count,
                    )
                # 4 deps_met
                done_ids = {w.wp_id for w in topo.wp_list if w.state == State.DONE}
                unmet = [d for d in wp.deps if d not in done_ids]
                if unmet:
                    raise DepsNotMetError(wp_id=wp_id, unmet_deps=unmet)

            # 落盘跃迁
            wp.state = to_state
            assert self._g is not None
            self._g.nodes[wp_id]["state"] = str(to_state)
            new_running = sum(1 for w in topo.wp_list if w.state == State.RUNNING)
            topo.current_running_count = new_running
            self._version = _new_version()
        self._emit(
            "L1-03:wp_state_changed",
            {
                "wp_id": wp_id,
                "from_state": str(from_state),
                "to_state": str(to_state),
                "reason": reason,
                "topology_version": self._version,
            },
        )

    def mark_stuck(self, wp_id: str) -> None:
        """仅 FAILED→STUCK 合法 · 由 L2-05 在连续失败 ≥ 3 时调用。"""
        # 先 probe wp 存在（找不到 raise WPNotFoundError · 语义对齐 transition_state）
        with self._lock:
            self._find_wp_unlocked(wp_id)
        self.transition_state(wp_id, State.FAILED, State.STUCK, reason="stuck")

    # ----- 查询 -----

    def can_lock_new_wp(self) -> bool:
        with self._lock:
            topo = self._require_loaded()
            return topo.current_running_count < topo.parallelism_limit

    def find_wp(self, wp_id: str) -> WorkPackage | None:
        with self._lock:
            if self._topology is None:
                return None
            for w in self._topology.wp_list:
                if w.wp_id == wp_id:
                    return w.model_copy()
            return None

    def read_snapshot(
        self,
        wp_ids: list[str] | None = None,
    ) -> TopologySnapshot:
        return read_snapshot(self, wp_ids)

    def _build_snapshot_payload(
        self,
        wp_ids: list[str] | None,
    ) -> dict[str, Any]:
        with self._lock:
            topo = self._require_loaded()
            ids = wp_ids if wp_ids is not None else [w.wp_id for w in topo.wp_list]
            id_set = set(ids)
            wp_states: dict[str, State] = {}
            wp_effort: dict[str, float] = {}
            deps: dict[str, list[str]] = {}
            for w in topo.wp_list:
                if w.wp_id not in id_set:
                    continue
                wp_states[w.wp_id] = w.state
                wp_effort[w.wp_id] = w.effort_estimate
                deps[w.wp_id] = list(w.deps)
            return {
                "project_id": topo.project_id,
                "topology_id": topo.topology_id,
                "topology_version": self._version,
                "wp_states": wp_states,
                "wp_effort": wp_effort,
                "deps": deps,
                "critical_path": list(topo.critical_path.wp_ids),
                "current_running_count": topo.current_running_count,
                "parallelism_limit": topo.parallelism_limit,
            }

    def export_readonly_view(self) -> dict[str, Any]:
        """完整聚合的 dict 表示（UI / 监督消费）· 深拷贝."""
        with self._lock:
            topo = self._require_loaded()
            return {
                "project_id": topo.project_id,
                "topology_id": topo.topology_id,
                "topology_version": self._version,
                "parallelism_limit": topo.parallelism_limit,
                "current_running_count": topo.current_running_count,
                "critical_path": list(topo.critical_path.wp_ids),
                "wp_list": [w.model_dump() for w in topo.wp_list],
                "dag_edges": [e.model_dump() for e in topo.dag_edges],
            }

    @property
    def topology_version(self) -> str:
        with self._lock:
            return self._version

    @property
    def topology(self) -> WBSTopology | None:
        with self._lock:
            return None if self._topology is None else self._topology.model_copy()

    def descendants_of(self, wp_id: str) -> set[str]:
        """某 WP 的下游集合（差量拆解用）。"""
        with self._lock:
            self._require_loaded()
            assert self._g is not None
            return descendants(self._g, wp_id)

    def topological_layers(self) -> list[list[str]]:
        with self._lock:
            self._require_loaded()
            assert self._g is not None
            return topological_generations(self._g)

    # ----- 内部 -----

    def _require_loaded(self) -> WBSTopology:
        if self._topology is None:
            raise RuntimeError("topology 尚未装图（调 load_topology 之前）")
        return self._topology

    def _find_wp_unlocked(self, wp_id: str) -> WorkPackage:
        topo = self._require_loaded()
        for w in topo.wp_list:
            if w.wp_id == wp_id:
                return w
        raise WPNotFoundError(wp_id=wp_id)

    def _emit(self, event_type: str, content: dict[str, Any]) -> None:
        """对外事件出口（IC-L2-08 → IC-09）。bus 未接 → 静默（单测无 bus 也要能跑）。"""
        if self._event_bus is None:
            return
        try:
            self._event_bus.append(
                event_type=event_type,
                content=content,
                project_id=self.project_id,
            )
        except Exception as exc:  # noqa: BLE001 — bus 故障不影响主流程 · 单测可 assert
            from app.l1_03.common.errors import EventAppendError
            raise EventAppendError(event_type=event_type, reason=str(exc)) from exc


def _field_nonempty(wp: WorkPackage, field: str) -> bool:
    v = getattr(wp, field)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return True  # 允许 deps 为空列表（根节点）· 仅要求字段存在
    if isinstance(v, (int, float)):
        return v > 0
    return True  # pragma: no cover
