"""ε-WP01 · L2-02 拓扑图管理器单元测试（≥ 39 TC）。

严格覆盖：
- §1 State enum / LEGAL_TRANSITIONS / assert_transition
- §2 errors · 14 错误码类
- §3 ids · regex 校验
- §4 EventBusStub / SkillClientStub
- §5 schemas · WorkPackage / WBSTopology / DAGEdge / CriticalPath
- §6 DAG · build / acyclic / critical_path / topological_generations / descendants
- §7 Manager · load_topology 正向 + 5 错误路径
- §8 Manager · transition_state · LEGAL / stale / parallelism / deps_met
- §9 Manager · mark_stuck / can_lock / descendants / layers / read_snapshot / export

TC ID 遵循 3-2 TDD spec §1 的 `TC-L103-L202-xxx`。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.errors import (
    ERROR_CODE_INDEX,
    ERROR_CODES,
    ConsistencyBypassError,
    CrossProjectDepError,
    CycleError,
    DanglingDepsError,
    DepsNotMetError,
    EventAppendError,
    IllegalTransition,
    IncompleteWPError,
    L103Error,
    OversizeError,
    ParallelismCapError,
    PM14MismatchError,
    RebuildFailedError,
    RunningWPCannotBeDropped,
    StaleStateError,
    WPNotFoundError,
)
from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.common.skill_client_stub import SkillClientStub
from app.l1_03.topology.dag import (
    assert_acyclic,
    build_digraph,
    compute_critical_path,
    descendants,
    topological_generations,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import (
    EFFORT_LIMIT_DAYS,
    CriticalPath,
    DAGEdge,
    WBSTopology,
    WorkPackage,
)
from app.l1_03.topology.snapshot import TopologySnapshot
from app.l1_03.topology.state_machine import (
    LEGAL_TRANSITIONS,
    State,
    assert_transition,
    is_legal,
)

# =====================================================================
# §1 State enum / LEGAL_TRANSITIONS
# =====================================================================

class TestStateMachineTransitions:
    def test_TC_L103_L202_014_legal_transitions_is_frozenset_of_7(self) -> None:
        """LEGAL_TRANSITIONS 是 frozenset 恰 7 条 · architecture §5.4 正解。"""
        assert isinstance(LEGAL_TRANSITIONS, frozenset)
        assert len(LEGAL_TRANSITIONS) == 7
        assert (State.READY, State.RUNNING) in LEGAL_TRANSITIONS
        assert (State.RUNNING, State.DONE) in LEGAL_TRANSITIONS
        assert (State.RUNNING, State.FAILED) in LEGAL_TRANSITIONS
        assert (State.FAILED, State.READY) in LEGAL_TRANSITIONS
        assert (State.FAILED, State.STUCK) in LEGAL_TRANSITIONS
        assert (State.READY, State.BLOCKED) in LEGAL_TRANSITIONS
        assert (State.BLOCKED, State.READY) in LEGAL_TRANSITIONS

    def test_state_enum_has_six_values(self) -> None:
        assert {str(s) for s in State} == {"READY", "RUNNING", "DONE", "FAILED", "BLOCKED", "STUCK"}

    def test_is_legal_rejects_illegal_pairs(self) -> None:
        assert is_legal(State.READY, State.RUNNING) is True
        assert is_legal(State.DONE, State.RUNNING) is False
        assert is_legal(State.STUCK, State.READY) is False  # STUCK 不可主动出
        assert is_legal(State.DONE, State.DONE) is False

    def test_assert_transition_raises_illegal(self) -> None:
        with pytest.raises(IllegalTransition) as exc:
            assert_transition(State.DONE, State.RUNNING, "wp-01")
        assert exc.value.code == "E_L103_L202_303"
        assert exc.value.wp_id == "wp-01"

    def test_assert_transition_ok_on_legal_pair(self) -> None:
        # 不抛即通过
        assert_transition(State.READY, State.RUNNING, "wp-01")
        assert_transition(State.FAILED, State.STUCK, "wp-02")


# =====================================================================
# §2 Errors
# =====================================================================

class TestErrors:
    def test_cycle_error_carries_cycle(self) -> None:
        e = CycleError(cycle=[("wp-a", "wp-b"), ("wp-b", "wp-a")])
        assert e.code == "E_L103_L202_101"
        assert e.cycle == [("wp-a", "wp-b"), ("wp-b", "wp-a")]
        assert "E_L103_L202_101" in str(e)

    def test_oversize_error_carries_effort(self) -> None:
        e = OversizeError(wp_id="wp-x", effort=7.5)
        assert e.code == "E_L103_L202_104"
        assert e.effort == 7.5
        assert e.limit == 5.0

    def test_error_code_index_has_all_classes(self) -> None:
        """每个 error code 映射到一个具体 exception class · 14 + 补充。"""
        for code, cls in ERROR_CODE_INDEX.items():
            assert issubclass(cls, L103Error)
            assert cls.code == code

    def test_error_codes_constants_match(self) -> None:
        assert CycleError.code == ERROR_CODES.E_L103_L202_101
        assert IllegalTransition.code == ERROR_CODES.E_L103_L202_303
        assert ParallelismCapError.code == ERROR_CODES.E_L103_L202_301

    def test_each_error_has_structured_context(self) -> None:
        # 每个 error 都带 context dict · 不丢字段
        e1 = DanglingDepsError(wp_id="wp-x", missing_deps=["wp-nope"])
        assert e1.context == {"wp_id": "wp-x", "missing_deps": ["wp-nope"]}
        e2 = CrossProjectDepError(wp_id="wp-y", expected_pid="pid-a", got_pid="pid-b")
        assert e2.expected_pid == "pid-a"
        e3 = PM14MismatchError(wp_id="wp-z", expected_pid="pid-a", got_pid="pid-c")
        assert e3.code == "E_L103_L202_201"
        e4 = DepsNotMetError(wp_id="wp-w", unmet_deps=["wp-dep"])
        assert e4.code == "E_L103_L202_302"
        e5 = StaleStateError(wp_id="wp-s", expected_from="READY", actual="RUNNING")
        assert e5.code == "E_L103_L202_304"
        e6 = WPNotFoundError(wp_id="wp-missing")
        assert e6.code == "E_L103_L202_305"
        e7 = EventAppendError(event_type="x", reason="bus down")
        assert e7.code == "E_L103_L202_401"
        e8 = RebuildFailedError(reason="corrupt")
        assert e8.code == "E_L103_L202_402"
        e9 = ConsistencyBypassError(attempted="direct write")
        assert e9.code == "E_L103_L202_501"
        e10 = RunningWPCannotBeDropped(wp_id="wp-running")
        assert e10.code.startswith("E_L103_L201_")

    def test_incomplete_wp_error_fields(self) -> None:
        e = IncompleteWPError(wp_id="wp-x", missing_fields=["goal", "dod_expr_ref"])
        assert e.missing_fields == ["goal", "dod_expr_ref"]


# =====================================================================
# §3 IDs
# =====================================================================

class TestIds:
    def test_valid_ids_pass(self) -> None:
        from pydantic import BaseModel

        from app.l1_03.common.ids import HarnessFlowProjectId, TopologyId, WPId

        class _M(BaseModel):
            p: HarnessFlowProjectId
            w: WPId
            t: TopologyId

        m = _M(p="pid-alpha", w="wp-01", t="topo-v1")
        assert m.p == "pid-alpha"
        assert m.w == "wp-01"
        assert m.t == "topo-v1"

    def test_invalid_project_id_rejected(self) -> None:
        from pydantic import BaseModel

        from app.l1_03.common.ids import HarnessFlowProjectId

        class _M(BaseModel):
            p: HarnessFlowProjectId

        with pytest.raises(ValidationError):
            _M(p="nope-123")
        with pytest.raises(ValidationError):
            _M(p="pid-")  # empty body

    def test_invalid_wp_id_rejected(self) -> None:
        from pydantic import BaseModel

        from app.l1_03.common.ids import WPId

        class _M(BaseModel):
            w: WPId

        with pytest.raises(ValidationError):
            _M(w="task-01")
        with pytest.raises(ValidationError):
            _M(w="")


# =====================================================================
# §4 EventBusStub / SkillClientStub
# =====================================================================

class TestEventBusStub:
    def test_append_returns_receipt(self) -> None:
        bus = EventBusStub()
        r = bus.append(event_type="L1-03:test", content={"x": 1}, project_id="pid-a")
        assert r["event_id"].startswith("evt-")
        assert r["sequence"] == 1
        assert len(bus.events) == 1

    def test_append_empty_project_id_rejected(self) -> None:
        bus = EventBusStub()
        with pytest.raises(ValueError, match="PM-14"):
            bus.append(event_type="x", content={}, project_id="")

    def test_subscribe_receives_payload(self) -> None:
        bus = EventBusStub()
        received: list[dict] = []
        bus.subscribe(lambda p: received.append(p))
        bus.append(event_type="L1-03:foo", content={"a": 1}, project_id="pid-a")
        assert len(received) == 1
        assert received[0]["type"] == "L1-03:foo"
        assert received[0]["project_id"] == "pid-a"

    def test_reset_clears_events_and_subs(self) -> None:
        bus = EventBusStub()
        bus.subscribe(lambda _p: None)
        bus.append(event_type="x", content={}, project_id="pid-a")
        bus.reset()
        assert bus.events == []
        assert bus._subscribers == []  # noqa: SLF001

    def test_filter_by_type_and_pid(self) -> None:
        bus = EventBusStub()
        bus.append(event_type="t1", content={}, project_id="pid-a")
        bus.append(event_type="t2", content={}, project_id="pid-a")
        bus.append(event_type="t1", content={}, project_id="pid-b")
        assert len(bus.filter(event_type="t1")) == 2
        assert len(bus.filter(project_id="pid-b")) == 1
        assert len(bus.filter(event_type="t1", project_id="pid-a")) == 1


class TestSkillClientStub:
    def test_default_decompose_returns_fixture(self) -> None:
        client = SkillClientStub()
        out = client.invoke_skill("wbs.decompose", {"project_id": "pid-a"})
        assert "wp_list" in out
        assert len(out["wp_list"]) == 3
        assert all(w["project_id"] == "pid-a" for w in out["wp_list"])

    def test_unknown_capability_raises(self) -> None:
        client = SkillClientStub()
        with pytest.raises(NotImplementedError):
            client.invoke_skill("unknown.cap", {})

    def test_register_override(self) -> None:
        client = SkillClientStub()
        client.register("custom", lambda p: {"custom": True, "params": p})
        out = client.invoke_skill("custom", {"k": "v"})
        assert out == {"custom": True, "params": {"k": "v"}}
        assert ("custom", {"k": "v"}) in client.invocations


# =====================================================================
# §5 Schemas
# =====================================================================

class TestSchemas:
    def test_workpackage_4_elements_required(self, project_id: str) -> None:
        with pytest.raises(ValidationError):
            WorkPackage(
                wp_id="wp-01", project_id=project_id,
                goal="", dod_expr_ref="x", deps=[], effort_estimate=1.0,
            )
        with pytest.raises(ValidationError):
            WorkPackage(
                wp_id="wp-01", project_id=project_id,
                goal="x", dod_expr_ref="", deps=[], effort_estimate=1.0,
            )

    def test_workpackage_oversize_raises_oversize_error(self, project_id: str) -> None:
        with pytest.raises((OversizeError, ValidationError)) as exc:
            WorkPackage(
                wp_id="wp-01", project_id=project_id,
                goal="big", dod_expr_ref="dod", deps=[],
                effort_estimate=EFFORT_LIMIT_DAYS + 0.5,
            )
        # pydantic v2 会把 validator raise 包成 ValidationError
        # 直接检查 message 含 OversizeError 的指纹
        assert "L103_L202_104" in str(exc.value) or "粒度超限" in str(exc.value)

    def test_workpackage_effort_zero_or_negative_rejected(self, project_id: str) -> None:
        with pytest.raises(ValidationError):
            WorkPackage(
                wp_id="wp-01", project_id=project_id,
                goal="x", dod_expr_ref="y", deps=[], effort_estimate=0.0,
            )

    def test_workpackage_default_state_ready(self, project_id: str) -> None:
        wp = WorkPackage(
            wp_id="wp-01", project_id=project_id,
            goal="g", dod_expr_ref="d", deps=[], effort_estimate=1.0,
        )
        assert wp.state == State.READY
        assert wp.failure_count == 0

    def test_workpackage_deps_must_be_strings(self, project_id: str) -> None:
        with pytest.raises(ValidationError):
            WorkPackage(
                wp_id="wp-01", project_id=project_id,
                goal="g", dod_expr_ref="d", deps=[""],  # empty str in list
                effort_estimate=1.0,
            )

    def test_dag_edge_frozen_hashable(self) -> None:
        e1 = DAGEdge(from_wp_id="a", to_wp_id="b")
        e2 = DAGEdge(from_wp_id="a", to_wp_id="b")
        assert {e1, e2} == {e1}  # hash 去重

    def test_critical_path_as_set(self) -> None:
        cp = CriticalPath(wp_ids=["wp-a", "wp-b", "wp-c"])
        assert len(cp) == 3
        assert "wp-a" in cp
        assert cp.as_set() == frozenset({"wp-a", "wp-b", "wp-c"})


# =====================================================================
# §6 DAG
# =====================================================================

class TestDAG:
    def test_build_digraph_nodes_and_edges(self, project_id: str, make_wp) -> None:
        wps = [make_wp("wp-a"), make_wp("wp-b", deps=["wp-a"])]
        edges = [DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b")]
        g = build_digraph(wps, edges)
        assert set(g.nodes) == {"wp-a", "wp-b"}
        assert ("wp-a", "wp-b") in g.edges
        assert g.nodes["wp-a"]["effort"] == 1.0

    def test_assert_acyclic_rejects_cycle(self, make_wp) -> None:
        wps = [make_wp("wp-a"), make_wp("wp-b")]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-b", to_wp_id="wp-a"),
        ]
        g = build_digraph(wps, edges)
        with pytest.raises(CycleError) as exc:
            assert_acyclic(g)
        assert exc.value.code == "E_L103_L202_101"
        assert len(exc.value.cycle) >= 1

    def test_compute_critical_path_picks_longest_effort(self, make_wp) -> None:
        wps = [
            make_wp("wp-a", effort_estimate=1.0),
            make_wp("wp-b", effort_estimate=5.0, deps=["wp-a"]),
            make_wp("wp-c", effort_estimate=2.0, deps=["wp-a"]),
        ]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-c"),
        ]
        g = build_digraph(wps, edges)
        path = compute_critical_path(g)
        assert path == ["wp-a", "wp-b"]  # 5.0+1.0 > 2.0+1.0

    def test_compute_critical_path_empty_graph(self) -> None:
        import networkx as nx
        g: nx.DiGraph = nx.DiGraph()
        assert compute_critical_path(g) == []

    def test_topological_generations_returns_layers(self, make_wp) -> None:
        wps = [
            make_wp("wp-a"),
            make_wp("wp-b", deps=["wp-a"]),
            make_wp("wp-c", deps=["wp-a"]),
            make_wp("wp-d", deps=["wp-b", "wp-c"]),
        ]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-c"),
            DAGEdge(from_wp_id="wp-b", to_wp_id="wp-d"),
            DAGEdge(from_wp_id="wp-c", to_wp_id="wp-d"),
        ]
        g = build_digraph(wps, edges)
        layers = topological_generations(g)
        assert layers == [["wp-a"], ["wp-b", "wp-c"], ["wp-d"]]

    def test_descendants_of_node(self, make_wp) -> None:
        wps = [
            make_wp("wp-a"),
            make_wp("wp-b", deps=["wp-a"]),
            make_wp("wp-c", deps=["wp-b"]),
        ]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-b", to_wp_id="wp-c"),
        ]
        g = build_digraph(wps, edges)
        assert descendants(g, "wp-a") == {"wp-b", "wp-c"}
        assert descendants(g, "wp-missing") == set()


# =====================================================================
# §7 Manager · load_topology
# =====================================================================

class TestManagerLoadTopology:
    def test_TC_L103_L202_001_load_full_returns_topology(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-001 · full 装图 · 3 WP · critical_path 非空。"""
        topo = manager.load_topology(
            linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"]
        )
        assert isinstance(topo, WBSTopology)
        assert topo.project_id == linear_wbs_draft["project_id"]
        assert topo.topology_id.startswith("topo-")
        assert len(topo.wp_list) == 3
        assert topo.critical_path.wp_ids == ["wp-001", "wp-002", "wp-003"]
        assert manager.topology_version != ""
        assert manager.topology is not None

    def test_TC_L103_L202_101_load_cycle_rejected(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-101 · 有环 → CycleError。"""
        wps = [make_wp("wp-a"), make_wp("wp-b", deps=["wp-a"])]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-b", to_wp_id="wp-a"),
        ]
        with pytest.raises(CycleError):
            manager.load_topology(wps, edges)

    def test_TC_L103_L202_102_load_dangling_deps_rejected(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-102 · deps 指向不存在 wp_id。"""
        wps = [make_wp("wp-a", deps=["wp-nope"])]
        with pytest.raises(DanglingDepsError) as exc:
            manager.load_topology(wps, [])
        assert "wp-nope" in exc.value.missing_deps

    def test_TC_L103_L202_103_load_incomplete_wp_rejected_by_pydantic(
        self, project_id: str,
    ) -> None:
        """TC-L103-L202-103 · 4 要素缺失 · pydantic 层就拦。"""
        with pytest.raises(ValidationError):
            WorkPackage(
                wp_id="wp-x", project_id=project_id,
                goal="", dod_expr_ref="d", deps=[], effort_estimate=1.0,
            )

    def test_TC_L103_L202_104_load_oversize_rejected(self) -> None:
        """TC-L103-L202-104 · effort > 5 → OversizeError（pydantic 包装）。"""
        with pytest.raises((OversizeError, ValidationError)):
            WorkPackage(
                wp_id="wp-big", project_id="pid-x",
                goal="big", dod_expr_ref="d", deps=[],
                effort_estimate=6.0,
            )

    def test_TC_L103_L202_106_pm14_mismatch_rejected(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-106 · WP.project_id != manager.project_id。"""
        wp_wrong = make_wp("wp-x", proj="pid-other-project")
        with pytest.raises(PM14MismatchError) as exc:
            manager.load_topology([wp_wrong], [])
        assert exc.value.code == "E_L103_L202_201"

    def test_emit_wbs_decomposed_after_load(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
        event_bus: EventBusStub, project_id: str,
    ) -> None:
        """装图完成 → IC-09 发 L1-03:wbs_decomposed 事件。"""
        manager.load_topology(
            linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"]
        )
        ev = event_bus.filter(event_type="L1-03:wbs_decomposed")
        assert len(ev) == 1
        assert ev[0].project_id == project_id
        assert ev[0].content["wp_count"] == 3


# =====================================================================
# §8 Manager · transition_state
# =====================================================================

class TestManagerTransition:
    def test_TC_L103_L202_005_ready_to_running_ok(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-005 · READY→RUNNING 成功 · running_count +1。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        topo = manager.topology
        assert topo is not None
        assert topo.current_running_count == 1
        wp = manager.find_wp("wp-001")
        assert wp is not None and wp.state == State.RUNNING

    def test_TC_L103_L202_006_running_to_done_ok(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-006 · RUNNING→DONE · running_count -1。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state("wp-001", State.RUNNING, State.DONE)
        topo = manager.topology
        assert topo is not None
        assert topo.current_running_count == 0

    def test_TC_L103_L202_109_illegal_transition_raises(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-109 · DONE→RUNNING 非法。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        with pytest.raises(IllegalTransition):
            manager.transition_state("wp-001", State.DONE, State.RUNNING)

    def test_TC_L103_L202_110_stale_state_detected(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-110 · 当前是 READY，调 transition(from=RUNNING) → stale。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        with pytest.raises(StaleStateError):
            manager.transition_state("wp-001", State.RUNNING, State.DONE)

    def test_TC_L103_L202_107_parallelism_cap_enforced(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-107 · 2 WP RUNNING · 第 3 个 READY→RUNNING 拒绝。"""
        wps = [make_wp("wp-a"), make_wp("wp-b"), make_wp("wp-c")]
        manager.load_topology(wps, [])
        manager.transition_state("wp-a", State.READY, State.RUNNING)
        manager.transition_state("wp-b", State.READY, State.RUNNING)
        with pytest.raises(ParallelismCapError):
            manager.transition_state("wp-c", State.READY, State.RUNNING)

    def test_TC_L103_L202_108_deps_not_met_rejected(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-108 · wp-002 deps=[wp-001]，wp-001 未 DONE · 拒绝 RUNNING。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        with pytest.raises(DepsNotMetError):
            manager.transition_state("wp-002", State.READY, State.RUNNING)

    def test_TC_L103_L202_111_wp_not_found(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-111 · 不存在 wp_id → WPNotFoundError。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        with pytest.raises(WPNotFoundError):
            manager.transition_state("wp-ghost", State.READY, State.RUNNING)

    def test_TC_L103_L202_008_mark_stuck_legal(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-008 · FAILED→STUCK via mark_stuck。"""
        wps = [make_wp("wp-a")]
        manager.load_topology(wps, [])
        manager.transition_state("wp-a", State.READY, State.RUNNING)
        manager.transition_state("wp-a", State.RUNNING, State.FAILED)
        manager.mark_stuck("wp-a")
        wp = manager.find_wp("wp-a")
        assert wp is not None and wp.state == State.STUCK

    def test_emit_state_changed_event_after_transition(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
        event_bus: EventBusStub,
    ) -> None:
        """每次 transition 都 emit L1-03:wp_state_changed。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        event_bus.reset()
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        ev = event_bus.filter(event_type="L1-03:wp_state_changed")
        assert len(ev) == 1
        assert ev[0].content["wp_id"] == "wp-001"
        assert ev[0].content["from_state"] == "READY"
        assert ev[0].content["to_state"] == "RUNNING"


# =====================================================================
# §9 Manager · snapshot / readonly / misc
# =====================================================================

class TestManagerSnapshotAndMisc:
    def test_TC_L103_L202_003_read_snapshot_full(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-003 · read_snapshot · frozen · 结构完整。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        snap = manager.read_snapshot()
        assert isinstance(snap, TopologySnapshot)
        assert snap.project_id == linear_wbs_draft["project_id"]
        assert set(snap.wp_states.keys()) == {"wp-001", "wp-002", "wp-003"}
        assert snap.wp_states["wp-001"] == State.READY
        # frozen：改不动
        with pytest.raises(ValidationError):
            snap.project_id = "pid-hack"  # type: ignore[misc]

    def test_TC_L103_L202_004_read_snapshot_subset(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-004 · read_snapshot(wp_ids=[...]) 只含指定 id。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        snap = manager.read_snapshot(wp_ids=["wp-001"])
        assert set(snap.wp_states.keys()) == {"wp-001"}

    def test_topology_snapshot_deps_met_helper(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        snap = manager.read_snapshot()
        # 根节点 deps_met=True · 下游要求父 DONE
        assert snap.deps_met("wp-001") is True
        assert snap.deps_met("wp-002") is False

    def test_TC_L103_L202_009_export_readonly_view(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """TC-L103-L202-009 · export_readonly_view · deep copy · 改不到内部。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        view = manager.export_readonly_view()
        assert view["project_id"] == linear_wbs_draft["project_id"]
        assert len(view["wp_list"]) == 3
        # 尝试篡改 view 不影响 manager
        view["wp_list"][0]["state"] = "HACKED"
        assert manager.find_wp("wp-001").state == State.READY  # type: ignore[union-attr]

    def test_TC_L103_L202_016_can_lock_new_wp(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        """TC-L103-L202-016 · can_lock_new_wp 反映当前 running 位。"""
        wps = [make_wp("wp-a"), make_wp("wp-b"), make_wp("wp-c")]
        manager.load_topology(wps, [])
        assert manager.can_lock_new_wp() is True  # 0 running
        manager.transition_state("wp-a", State.READY, State.RUNNING)
        assert manager.can_lock_new_wp() is True  # 1 running
        manager.transition_state("wp-b", State.READY, State.RUNNING)
        assert manager.can_lock_new_wp() is False  # 2 running · 已到 cap

    def test_descendants_of(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        assert manager.descendants_of("wp-001") == {"wp-002", "wp-003"}
        assert manager.descendants_of("wp-003") == set()

    def test_topological_layers(
        self, manager: WBSTopologyManager, make_wp,
    ) -> None:
        wps = [
            make_wp("wp-a"),
            make_wp("wp-b", deps=["wp-a"]),
            make_wp("wp-c", deps=["wp-a"]),
        ]
        edges = [
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b"),
            DAGEdge(from_wp_id="wp-a", to_wp_id="wp-c"),
        ]
        manager.load_topology(wps, edges)
        assert manager.topological_layers() == [["wp-a"], ["wp-b", "wp-c"]]

    def test_manager_requires_project_id(self) -> None:
        with pytest.raises(ValueError, match="PM-14"):
            WBSTopologyManager(project_id="")

    def test_topology_version_changes_on_write(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
    ) -> None:
        """每次写操作（load / transition）topology_version 都变。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        v1 = manager.topology_version
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        v2 = manager.topology_version
        assert v1 != v2
        assert v1.startswith("v-") and v2.startswith("v-")


# =====================================================================
# 补充 · 集成 / IC-L2-08 幂等性
# =====================================================================

class TestIntegrationLite:
    def test_TC_L103_L202_606_append_event_on_every_transition(
        self, manager: WBSTopologyManager, linear_wbs_draft: dict,
        event_bus: EventBusStub,
    ) -> None:
        """TC-L103-L202-606 · IC-L2-08 → IC-09 · 每次跃迁都 append。"""
        manager.load_topology(linear_wbs_draft["wp_list"], linear_wbs_draft["dag_edges"])
        n0 = len(event_bus.events)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state("wp-001", State.RUNNING, State.DONE)
        assert len(event_bus.events) == n0 + 2

    def test_event_bus_none_means_silent_no_error(
        self, project_id: str, make_wp,
    ) -> None:
        """event_bus=None · 装图 / 跃迁仍正常（bus 可选）。"""
        m = WBSTopologyManager(project_id=project_id, event_bus=None)
        wps = [make_wp("wp-a")]
        m.load_topology(wps, [])
        m.transition_state("wp-a", State.READY, State.RUNNING)
        wp = m.find_wp("wp-a")
        assert wp is not None and wp.state == State.RUNNING
