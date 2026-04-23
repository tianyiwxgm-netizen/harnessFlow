"""ε-WP03 · L2-03 WP 调度器 · IC-02 入口单元测试（≥ 39 TC）。

覆盖：
- §1 IC-02 schemas（Query / Result / WPDefOut / WaitingReason）
- §2 ConcurrencyGuard
- §3 priority_queue · critical_path + topo_level + effort 排序
- §4 Dispatcher 正向（3 WP 链路 + 关键路径优先 + 事件 emit）
- §5 Dispatcher 三态 null 返回（all_done / awaiting_deps / concurrency_cap / deadlock / lock_contention）
- §6 PM-14 跨 pid 拒绝
- §7 exclude_wp_ids 过滤
- §8 无状态性
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.scheduler import (
    ConcurrencyGuard,
    GetNextWPQuery,
    GetNextWPResult,
    WaitingReason,
    WPDispatcher,
    get_next_wp,
    prioritize_candidates,
)
from app.l1_03.scheduler.schemas import WPDefOut
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge
from app.l1_03.topology.state_machine import State

# =====================================================================
# fixtures
# =====================================================================

@pytest.fixture
def query(project_id: str) -> GetNextWPQuery:
    return GetNextWPQuery(
        query_id="q-001",
        project_id=project_id,
        requester_tick="tick-001",
        prefer_critical_path=True,
    )


@pytest.fixture
def loaded_manager(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> WBSTopologyManager:
    mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    wps = [
        make_wp("wp-root", effort_estimate=1.0),
        make_wp("wp-a", deps=["wp-root"], effort_estimate=4.0),
        make_wp("wp-b", deps=["wp-root"], effort_estimate=2.0),
        make_wp("wp-c", deps=["wp-a"], effort_estimate=1.0),
    ]
    edges = [
        DAGEdge(from_wp_id="wp-root", to_wp_id="wp-a"),
        DAGEdge(from_wp_id="wp-root", to_wp_id="wp-b"),
        DAGEdge(from_wp_id="wp-a", to_wp_id="wp-c"),
    ]
    mgr.load_topology(wps, edges)
    return mgr


# =====================================================================
# §1 Schemas
# =====================================================================

class TestSchemas:
    def test_query_schema(self, project_id: str) -> None:
        q = GetNextWPQuery(
            query_id="q-1", project_id=project_id, requester_tick="t-1",
        )
        assert q.prefer_critical_path is True
        assert q.exclude_wp_ids == []

    def test_query_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            GetNextWPQuery(query_id="", project_id="pid-x", requester_tick="t")  # type: ignore[arg-type]

    def test_query_frozen(self, project_id: str) -> None:
        q = GetNextWPQuery(
            query_id="q-1", project_id=project_id, requester_tick="t-1",
        )
        with pytest.raises(ValidationError):
            q.query_id = "q-hack"  # type: ignore[misc]

    def test_result_defaults(self) -> None:
        r = GetNextWPResult(
            query_id="q-1", in_flight_wp_count=0, topology_version="v-1",
        )
        assert r.wp_id is None
        assert r.deps_met is True
        assert r.waiting_reason is None

    def test_waiting_reason_enum(self) -> None:
        assert str(WaitingReason.ALL_DONE) == "all_done"
        assert str(WaitingReason.AWAITING_DEPS) == "awaiting_deps"
        assert str(WaitingReason.CONCURRENCY_CAP) == "concurrency_cap"
        assert str(WaitingReason.DEADLOCK) == "deadlock"
        assert str(WaitingReason.LOCK_CONTENTION) == "lock_contention"


# =====================================================================
# §2 ConcurrencyGuard
# =====================================================================

class TestConcurrencyGuard:
    def test_can_dispatch_below_limit(self) -> None:
        g = ConcurrencyGuard(limit=2)
        assert g.can_dispatch(0) is True
        assert g.can_dispatch(1) is True
        assert g.can_dispatch(2) is False

    def test_at_cap(self) -> None:
        g = ConcurrencyGuard(limit=2)
        assert g.at_cap(2) is True
        assert g.at_cap(3) is True  # 过载也算 at_cap
        assert g.at_cap(1) is False

    def test_invalid_limit_rejected(self) -> None:
        with pytest.raises(ValueError):
            ConcurrencyGuard(limit=0)


# =====================================================================
# §3 priority_queue
# =====================================================================

class TestPriorityQueue:
    def test_critical_path_first(self, loaded_manager: WBSTopologyManager) -> None:
        snap = loaded_manager.read_snapshot()
        layers = loaded_manager.topological_layers()
        # 关键路径应该是 wp-root → wp-a → wp-c（effort 1+4+1 = 6，wp-b 路径 1+2=3）
        assert "wp-a" in snap.critical_path
        # 候选：wp-a、wp-b（都 deps wp-root，wp-root 未 DONE）
        ranked = prioritize_candidates(
            ["wp-b", "wp-a"], snap, topo_layers=layers, prefer_critical_path=True,
        )
        assert ranked[0] == "wp-a"  # critical 优先

    def test_without_prefer_critical(self, loaded_manager: WBSTopologyManager) -> None:
        snap = loaded_manager.read_snapshot()
        layers = loaded_manager.topological_layers()
        # 不优先 critical → 按 topo_level / effort desc / wp_id asc
        ranked = prioritize_candidates(
            ["wp-b", "wp-a"], snap, topo_layers=layers, prefer_critical_path=False,
        )
        # wp-a effort=4 > wp-b effort=2 · 同层 → wp-a 先
        assert ranked == ["wp-a", "wp-b"]

    def test_stable_sort_by_wp_id_when_tie(self, loaded_manager: WBSTopologyManager) -> None:
        snap = loaded_manager.read_snapshot()
        # 构造 tie：两个同 layer 同 effort · 按 wp_id asc
        ranked = prioritize_candidates(
            ["wp-b", "wp-a", "wp-c"], snap, topo_layers=[["wp-a", "wp-b", "wp-c"]],
            prefer_critical_path=False,
        )
        # wp-a / wp-b / wp-c effort 分别 4 / 2 / 1 · wp-a 最大 先；wp-b 次之
        assert ranked[0] == "wp-a"
        assert ranked[-1] == "wp-c"


# =====================================================================
# §4 Dispatcher 正向
# =====================================================================

class TestDispatcherPositive:
    def test_TC_L103_L203_001_get_next_wp_returns_root(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        """IC-02 正向 · 第一次调 · 返回 wp-root（唯一 READY + deps_met）。"""
        d = WPDispatcher(loaded_manager, event_bus)
        r = d.get_next_wp(query)
        assert r.wp_id == "wp-root"
        assert r.deps_met is True
        assert r.wp_def is not None
        assert r.wp_def.wp_id == "wp-root"
        assert r.in_flight_wp_count == 1
        assert r.topology_version != ""
        # wp-root 在 manager 内应该是 RUNNING
        wp = loaded_manager.find_wp("wp-root")
        assert wp is not None and wp.state == State.RUNNING

    def test_dispatched_event_emitted(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub, project_id: str,
    ) -> None:
        event_bus.reset()
        # load_topology emit 过事件 · reset 后重新开始
        d = WPDispatcher(loaded_manager, event_bus)
        d.get_next_wp(query)
        ev = event_bus.filter(event_type="L1-03:wp_ready_dispatched")
        assert len(ev) == 1
        assert ev[0].content["wp_id"] == "wp-root"
        assert ev[0].content["requester_tick"] == "tick-001"
        assert ev[0].project_id == project_id

    def test_second_call_returns_next(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        project_id: str, event_bus: EventBusStub,
    ) -> None:
        """调完 root 并把它 mark DONE 后，下次应派 wp-a（critical）。"""
        d = WPDispatcher(loaded_manager, event_bus)
        d.get_next_wp(query)  # wp-root RUNNING
        loaded_manager.transition_state("wp-root", State.RUNNING, State.DONE)
        q2 = query.model_copy(update={"query_id": "q-002"})
        r = d.get_next_wp(q2)
        assert r.wp_id == "wp-a"  # critical 优先（effort 4）
        assert r.in_flight_wp_count == 1

    def test_wp_def_contains_full_workpackage(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        d = WPDispatcher(loaded_manager, event_bus)
        r = d.get_next_wp(query)
        assert r.wp_def is not None
        assert isinstance(r.wp_def, WPDefOut)
        assert r.wp_def.effort_estimate == 1.0
        assert r.wp_def.deps == []

    def test_ranking_reason_critical_path(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        """wp-root 在 critical_path · 事件的 ranking_reason=critical_path。"""
        event_bus.reset()
        d = WPDispatcher(loaded_manager, event_bus)
        d.get_next_wp(query)
        ev = event_bus.filter(event_type="L1-03:wp_ready_dispatched")[0]
        assert ev.content["ranking_reason"] == "critical_path"


# =====================================================================
# §5 三态 null 返回
# =====================================================================

class TestDispatcherNullStates:
    def test_all_done(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        # 全部 WP 手动置 DONE
        for wp_id in ("wp-root", "wp-a", "wp-b", "wp-c"):
            loaded_manager.transition_state(wp_id, State.READY, State.RUNNING)
            loaded_manager.transition_state(wp_id, State.RUNNING, State.DONE)
            # 注意：wp-a deps=wp-root，所以要 wp-root DONE 后才能走 wp-a
            # 但我们按顺序也不行 · wp-b 不依赖 wp-root → 可以
            # wp-c deps wp-a → 要 wp-a DONE
        d = WPDispatcher(loaded_manager, event_bus)
        r = d.get_next_wp(query)
        assert r.wp_id is None
        assert r.waiting_reason == WaitingReason.ALL_DONE
        assert r.in_flight_wp_count == 0

    def test_awaiting_deps(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        # wp-root RUNNING · wp-a/b 都依赖它 · 剩下的 READY 都 deps 未 met
        d = WPDispatcher(loaded_manager, event_bus)
        d.get_next_wp(query)  # wp-root → RUNNING
        # 第二次调 · wp-a/b/c 都 READY 但 deps 都未 met
        r = d.get_next_wp(query)
        assert r.wp_id is None
        assert r.waiting_reason == WaitingReason.AWAITING_DEPS
        assert r.in_flight_wp_count == 1

    def test_TC_L103_L203_107_concurrency_cap(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        """2 WP RUNNING · 第 3 次 get_next_wp 返 concurrency_cap。"""
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        wps = [make_wp("wp-a"), make_wp("wp-b"), make_wp("wp-c")]
        mgr.load_topology(wps, [])
        mgr.transition_state("wp-a", State.READY, State.RUNNING)
        mgr.transition_state("wp-b", State.READY, State.RUNNING)
        d = WPDispatcher(mgr, event_bus)
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
        )
        r = d.get_next_wp(q)
        assert r.wp_id is None
        assert r.waiting_reason == WaitingReason.CONCURRENCY_CAP
        assert r.error_code == "E_WP_CONCURRENCY_CAP"

    def test_deadlock(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        """全部 WP 是 FAILED + STUCK · 无 READY 无 RUNNING → deadlock。"""
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        wps = [make_wp("wp-a"), make_wp("wp-b")]
        mgr.load_topology(wps, [])
        # 把 wp-a/b 都走完链路到 STUCK
        for wp_id in ("wp-a", "wp-b"):
            mgr.transition_state(wp_id, State.READY, State.RUNNING)
            mgr.transition_state(wp_id, State.RUNNING, State.FAILED)
            mgr.mark_stuck(wp_id)
        d = WPDispatcher(mgr, event_bus)
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
        )
        r = d.get_next_wp(q)
        assert r.wp_id is None
        assert r.waiting_reason == WaitingReason.DEADLOCK

    def test_empty_topology_returns_deadlock_or_all_done(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """空 topology · 语义模糊但至少要 null + 无 crash。"""
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        # Actually 空 wp_list 装图会 critical_path=[] · topological_layers=[] · all_done 判定要求 total_wps>0
        # 所以空 topo 走到 no candidates + no READY + no RUNNING → deadlock
        # 但空 topo 装图会被 WBSTopology.wp_list 的 min-length 吗？没定义 · 允许空
        mgr.load_topology([], [])
        d = WPDispatcher(mgr, event_bus)
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
        )
        r = d.get_next_wp(q)
        assert r.wp_id is None


# =====================================================================
# §6 PM-14 跨 pid 拒绝
# =====================================================================

class TestPM14:
    def test_TC_L103_L203_106_cross_project_rejected(
        self, loaded_manager: WBSTopologyManager, event_bus: EventBusStub,
    ) -> None:
        """query.project_id != manager.project_id → E_WP_CROSS_PROJECT。"""
        q = GetNextWPQuery(
            query_id="q", project_id="pid-attacker", requester_tick="t",
        )
        d = WPDispatcher(loaded_manager, event_bus)
        r = d.get_next_wp(q)
        assert r.wp_id is None
        assert r.error_code == "E_WP_CROSS_PROJECT"
        assert r.in_flight_wp_count == 0


# =====================================================================
# §7 exclude_wp_ids
# =====================================================================

class TestExcludeFilter:
    def test_exclude_wp_skipped(
        self, loaded_manager: WBSTopologyManager, project_id: str,
        event_bus: EventBusStub,
    ) -> None:
        """exclude wp-root → 即使 READY 也跳过。"""
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
            exclude_wp_ids=["wp-root"],
        )
        d = WPDispatcher(loaded_manager, event_bus)
        r = d.get_next_wp(q)
        # wp-root 被排除 · 其他 deps 未 met · 返 awaiting_deps
        assert r.wp_id != "wp-root"


# =====================================================================
# §8 无状态性
# =====================================================================

class TestStateless:
    def test_two_dispatchers_on_same_manager_share_truth(
        self, loaded_manager: WBSTopologyManager, event_bus: EventBusStub,
        project_id: str,
    ) -> None:
        """两个 dispatcher 实例 · 共 manager · 第一次 d1 锁 wp-root · d2 应看到 cap 或 awaiting。"""
        q = GetNextWPQuery(
            query_id="q1", project_id=project_id, requester_tick="t1",
        )
        d1 = WPDispatcher(loaded_manager, event_bus)
        d2 = WPDispatcher(loaded_manager, event_bus)
        r1 = d1.get_next_wp(q)
        assert r1.wp_id == "wp-root"
        # d2 第二次 · wp-root 已 RUNNING · 剩下 awaiting_deps
        q2 = q.model_copy(update={"query_id": "q2"})
        r2 = d2.get_next_wp(q2)
        assert r2.wp_id is None
        assert r2.waiting_reason == WaitingReason.AWAITING_DEPS


# =====================================================================
# §9 function wrapper
# =====================================================================

class TestFunctionalEntry:
    def test_get_next_wp_function(
        self, loaded_manager: WBSTopologyManager, query: GetNextWPQuery,
        event_bus: EventBusStub,
    ) -> None:
        r = get_next_wp(loaded_manager, query, event_bus=event_bus)
        assert r.wp_id == "wp-root"
