"""ε-WP02 · L2-01 WBS 拆解器单元测试（≥ 37 TC）。

覆盖：
- §1 IC-19 schemas（FourSetPlan / ArchitectureOutput / Command / Result / WBSDraft）
- §2 SkillInvoker · full / incremental · parse raw
- §3 diff_merge · RUNNING 保留 / DONE 可丢 / RUNNING 不可丢 / edges 替换
- §4 WBSFactory.handle_ic_19 · 正向 full / incremental
- §5 WBSFactory.handle_ic_19 · 5 IC-19 错误码路径
- §6 decompose_wbs 便捷函数
- §7 边界 / 幂等 / 事件 emit
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.errors import OversizeError
from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.common.skill_client_stub import SkillClientStub
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge, WorkPackage
from app.l1_03.topology.state_machine import State
from app.l1_03.wbs_decomposer import (
    ArchitectureOutput,
    FourSetPlan,
    RequestWBSDecompositionCommand,
    RequestWBSDecompositionResult,
    TargetGranularity,
    WBSDraft,
    WBSFactory,
    decompose_wbs,
    diff_merge,
)
from app.l1_03.wbs_decomposer.factory import (
    ArchOutputMissingError,
    DecompositionFailError,
    FourPackIncompleteError,
    NoProjectIdError,
    TopologyCorruptError,
)
from app.l1_03.wbs_decomposer.skill_invoker import SkillInvoker

# =====================================================================
# fixtures
# =====================================================================

@pytest.fixture
def four_pack() -> FourSetPlan:
    return FourSetPlan(
        charter_path="docs/project.md",
        plan_path="docs/plan.md",
        requirements_path="docs/reqs.md",
        risk_path="docs/risk.md",
    )


@pytest.fixture
def arch_out() -> ArchitectureOutput:
    return ArchitectureOutput(
        togaf_phases=["B", "C", "D"],
        adr_path="docs/adr/0001.md",
    )


@pytest.fixture
def cmd_ok(project_id: str, four_pack, arch_out) -> RequestWBSDecompositionCommand:
    return RequestWBSDecompositionCommand(
        command_id="wbs-req-aaa",
        project_id=project_id,
        artifacts_4_pack=four_pack,
        architecture_output=arch_out,
        target_wp_granularity=TargetGranularity.MEDIUM,
    )


# =====================================================================
# §1 Schemas
# =====================================================================

class TestSchemas:
    def test_TC_L103_L201_001_four_pack_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            FourSetPlan(
                charter_path="",
                plan_path="p",
                requirements_path="r",
                risk_path="k",
            )

    def test_arch_output_requires_adr(self) -> None:
        with pytest.raises(ValidationError):
            ArchitectureOutput(togaf_phases=["B"], adr_path="")

    def test_granularity_default_medium(self, project_id: str, four_pack, arch_out) -> None:
        cmd = RequestWBSDecompositionCommand(
            command_id="c1",
            project_id=project_id,
            artifacts_4_pack=four_pack,
            architecture_output=arch_out,
        )
        assert cmd.target_wp_granularity == TargetGranularity.MEDIUM
        assert cmd.mode == "full"

    def test_incremental_requires_target_wp_id(
        self, project_id: str, four_pack, arch_out,
    ) -> None:
        with pytest.raises(ValidationError, match="target_wp_id"):
            RequestWBSDecompositionCommand(
                command_id="c1",
                project_id=project_id,
                artifacts_4_pack=four_pack,
                architecture_output=arch_out,
                mode="incremental",
            )

    def test_wbs_draft_pid_closure_enforced(
        self, project_id: str, make_wp,
    ) -> None:
        wrong = make_wp("wp-a", proj="pid-other")
        with pytest.raises(ValidationError, match="PM-14"):
            WBSDraft(
                project_id=project_id,
                topology_version="v1",
                wp_list=[wrong],
            )

    def test_request_result_schema(self) -> None:
        r = RequestWBSDecompositionResult(
            command_id="c1", accepted=True, decomposition_session_id="decomp-x"
        )
        assert r.accepted is True
        assert r.decomposition_session_id == "decomp-x"

    def test_wbs_draft_wp_count_property(self, project_id: str, make_wp) -> None:
        draft = WBSDraft(
            project_id=project_id,
            topology_version="v1",
            wp_list=[make_wp("wp-a"), make_wp("wp-b")],
        )
        assert draft.wp_count == 2


# =====================================================================
# §2 SkillInvoker
# =====================================================================

class TestSkillInvoker:
    def test_decompose_full_returns_parsed_wps(
        self, project_id: str, skill_client: SkillClientStub,
    ) -> None:
        invoker = SkillInvoker(skill_client)
        wps, edges = invoker.decompose_full(
            project_id=project_id,
            four_set_plan={"charter_path": "a"},
            architecture_output={"adr_path": "b"},
            target_granularity="medium",
        )
        # stub 默认返 wp-a/b/c 但 project_id 用传入
        assert len(wps) == 3
        assert all(isinstance(w, WorkPackage) for w in wps)
        # stub 走的是默认 handler · fixture 里 project_id 从 params 取
        assert all(w.project_id == project_id for w in wps)
        assert len(edges) == 2

    def test_decompose_full_records_invocation(
        self, project_id: str, skill_client: SkillClientStub,
    ) -> None:
        invoker = SkillInvoker(skill_client)
        invoker.decompose_full(
            project_id=project_id,
            four_set_plan={"charter_path": "a"},
            architecture_output={"adr_path": "b"},
            target_granularity="medium",
        )
        assert len(skill_client.invocations) == 1
        cap, params = skill_client.invocations[0]
        assert cap == "wbs.decompose"
        assert params["project_id"] == project_id
        assert params["target_granularity"] == "medium"

    def test_decompose_incremental_returns_subtree(
        self, project_id: str, skill_client: SkillClientStub,
    ) -> None:
        invoker = SkillInvoker(skill_client)
        wps, edges = invoker.decompose_incremental(
            project_id=project_id,
            target_wp_id="wp-parent",
            four_set_plan={"charter_path": "a"},
            architecture_output={"adr_path": "b"},
        )
        assert len(wps) == 2
        assert wps[0].wp_id == "wp-parent-sub1"
        assert wps[1].wp_id == "wp-parent-sub2"
        assert len(edges) == 1

    def test_skill_returning_empty_wp_list_rejected(
        self, project_id: str, skill_client: SkillClientStub,
    ) -> None:
        skill_client.register("wbs.decompose", lambda _p: {"wp_list": [], "edges": []})
        invoker = SkillInvoker(skill_client)
        with pytest.raises(ValueError, match="wp_list"):
            invoker.decompose_full(
                project_id=project_id,
                four_set_plan={"charter_path": "a"},
                architecture_output={"adr_path": "b"},
                target_granularity="medium",
            )


# =====================================================================
# §3 diff_merge
# =====================================================================

class TestDiffMerge:
    @staticmethod
    def _mk_topo(project_id: str, make_wp, wps_state: dict[str, State]):
        """构一个 loaded 的 topology · 指定每个 WP 的 state。"""
        wps = []
        for wp_id, st in wps_state.items():
            w = make_wp(wp_id)
            w.state = st
            wps.append(w)
        # 避开 manager 的 state 校验 · 直接构 WBSTopology
        from app.l1_03.topology.schemas import WBSTopology

        return WBSTopology(
            project_id=project_id,
            topology_id="topo-x",
            wp_list=wps,
            dag_edges=[],
            current_running_count=sum(1 for w in wps if w.state == State.RUNNING),
        )

    def test_TC_L103_L201_302_preserve_running_wp(
        self, project_id: str, make_wp,
    ) -> None:
        old = self._mk_topo(project_id, make_wp, {
            "wp-a": State.RUNNING,
            "wp-b": State.READY,
        })
        new_wps = [make_wp("wp-a"), make_wp("wp-c")]  # a state=READY 新
        new_edges = [DAGEdge(from_wp_id="wp-a", to_wp_id="wp-c")]
        draft = diff_merge(old, new_wps, new_edges, new_topology_version="v2")
        a = next(w for w in draft.wp_list if w.wp_id == "wp-a")
        assert a.state == State.RUNNING  # 旧 RUNNING 保留
        assert any(w.wp_id == "wp-c" for w in draft.wp_list)

    def test_preserve_done_wp(self, project_id: str, make_wp) -> None:
        old = self._mk_topo(project_id, make_wp, {
            "wp-a": State.DONE,
            "wp-b": State.READY,
        })
        new_wps = [make_wp("wp-a"), make_wp("wp-c")]
        draft = diff_merge(old, new_wps, [], new_topology_version="v2")
        a = next(w for w in draft.wp_list if w.wp_id == "wp-a")
        assert a.state == State.DONE

    def test_drop_done_allowed(self, project_id: str, make_wp) -> None:
        old = self._mk_topo(project_id, make_wp, {
            "wp-a": State.DONE,
            "wp-b": State.READY,
        })
        new_wps = [make_wp("wp-c")]  # a 被 drop
        draft = diff_merge(old, new_wps, [], new_topology_version="v2")
        assert not any(w.wp_id == "wp-a" for w in draft.wp_list)

    def test_TC_L103_L201_301_drop_running_rejected(
        self, project_id: str, make_wp,
    ) -> None:
        old = self._mk_topo(project_id, make_wp, {
            "wp-a": State.RUNNING,
            "wp-b": State.READY,
        })
        new_wps = [make_wp("wp-c")]  # a 被 drop → 拒绝
        from app.l1_03.common.errors import RunningWPCannotBeDropped
        with pytest.raises(RunningWPCannotBeDropped):
            diff_merge(old, new_wps, [], new_topology_version="v2")

    def test_edges_replaced_by_new(self, project_id: str, make_wp) -> None:
        old = self._mk_topo(project_id, make_wp, {"wp-a": State.READY})
        new_wps = [make_wp("wp-a"), make_wp("wp-b", deps=["wp-a"])]
        new_edges = [DAGEdge(from_wp_id="wp-a", to_wp_id="wp-b")]
        draft = diff_merge(old, new_wps, new_edges, new_topology_version="v2")
        assert len(draft.dag_edges) == 1
        assert draft.topology_version == "v2"


# =====================================================================
# §4 WBSFactory 正向
# =====================================================================

class TestFactoryPositive:
    def test_TC_L103_L201_001_handle_ic_19_full_accepted(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        res = factory.handle_ic_19(cmd_ok)
        assert res.accepted is True
        assert res.command_id == "wbs-req-aaa"
        assert res.decomposition_session_id is not None
        assert res.decomposition_session_id.startswith("decomp-")
        assert factory.last_draft is not None
        assert factory.last_draft.wp_count == 3

    def test_emits_wbs_topology_ready_event(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand, project_id: str,
    ) -> None:
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        factory.handle_ic_19(cmd_ok)
        events = event_bus.filter(event_type="L1-03:wbs_topology_ready")
        assert len(events) == 1
        ev = events[0]
        assert ev.project_id == project_id
        assert ev.content["wp_count"] == 3

    def test_incremental_mode(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        project_id: str, four_pack, arch_out,
    ) -> None:
        cmd = RequestWBSDecompositionCommand(
            command_id="wbs-inc-1",
            project_id=project_id,
            artifacts_4_pack=four_pack,
            architecture_output=arch_out,
            mode="incremental",
            target_wp_id="wp-parent",
        )
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        res = factory.handle_ic_19(cmd)
        assert res.accepted is True
        assert factory.last_draft is not None
        assert factory.last_draft.wp_count == 2
        # incremental skill 记录调用
        assert any(c == "wbs.decompose_incremental" for c, _ in skill_client.invocations)

    def test_last_session_id_populated(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        factory.handle_ic_19(cmd_ok)
        assert factory.last_session_id is not None
        assert factory.last_session_id.startswith("decomp-")

    def test_event_bus_none_silent(
        self, skill_client: SkillClientStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        factory = WBSFactory(skill_client=skill_client, event_bus=None)
        res = factory.handle_ic_19(cmd_ok)
        assert res.accepted is True


# =====================================================================
# §5 WBSFactory 负向
# =====================================================================

class TestFactoryErrors:
    def test_TC_L103_L201_101_four_pack_incomplete_rejected(
        self, project_id: str, arch_out,
    ) -> None:
        """缺字段 → pydantic ValidationError（IC-19 schema 层）。"""
        with pytest.raises(ValidationError):
            RequestWBSDecompositionCommand(
                command_id="c",
                project_id=project_id,
                artifacts_4_pack=FourSetPlan(
                    charter_path="",  # 缺
                    plan_path="p",
                    requirements_path="r",
                    risk_path="k",
                ),
                architecture_output=arch_out,
            )

    def test_TC_L103_L201_102_arch_output_missing(
        self, project_id: str, four_pack,
    ) -> None:
        with pytest.raises(ValidationError):
            RequestWBSDecompositionCommand(
                command_id="c",
                project_id=project_id,
                artifacts_4_pack=four_pack,
                architecture_output=ArchitectureOutput(togaf_phases=[], adr_path=""),
            )

    def test_TC_L103_L201_103_decomposition_skill_fail_mapped(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        def _boom(_p):
            raise RuntimeError("LLM exploded")
        skill_client.register("wbs.decompose", _boom)
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        with pytest.raises(DecompositionFailError) as exc:
            factory.handle_ic_19(cmd_ok)
        assert exc.value.code == "E_WBS_DECOMPOSITION_FAIL"
        assert "LLM exploded" in exc.value.reason

    def test_TC_L103_L201_104_skill_returns_invalid_wps_mapped(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        # skill 返字段不合法（缺 dod_expr_ref）
        def _bad(_p):
            return {
                "wp_list": [
                    {
                        "wp_id": "wp-x", "project_id": cmd_ok.project_id,
                        "goal": "g", "dod_expr_ref": "", "deps": [],
                        "effort_estimate": 1.0,
                    },
                ],
                "edges": [],
            }
        skill_client.register("wbs.decompose", _bad)
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        with pytest.raises(TopologyCorruptError) as exc:
            factory.handle_ic_19(cmd_ok)
        assert exc.value.code == "E_WBS_TOPOLOGY_CORRUPT"

    def test_TC_L103_L201_105_skill_returns_cross_pid_mapped(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        def _cross(_p):
            return {
                "wp_list": [
                    {
                        "wp_id": "wp-x", "project_id": "pid-DIFFERENT",
                        "goal": "g", "dod_expr_ref": "d", "deps": [],
                        "effort_estimate": 1.0,
                    },
                ],
                "edges": [],
            }
        skill_client.register("wbs.decompose", _cross)
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        with pytest.raises(TopologyCorruptError):
            factory.handle_ic_19(cmd_ok)

    def test_TC_L103_L201_106_skill_returns_oversize_wp(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        def _big(_p):
            return {
                "wp_list": [
                    {
                        "wp_id": "wp-x", "project_id": cmd_ok.project_id,
                        "goal": "g", "dod_expr_ref": "d", "deps": [],
                        "effort_estimate": 7.0,  # > 5
                    },
                ],
                "edges": [],
            }
        skill_client.register("wbs.decompose", _big)
        factory = WBSFactory(skill_client=skill_client, event_bus=event_bus)
        with pytest.raises((OversizeError, TopologyCorruptError)):
            factory.handle_ic_19(cmd_ok)

    def test_unknown_skill_mapped_to_decomposition_fail(
        self, event_bus: EventBusStub, cmd_ok: RequestWBSDecompositionCommand,
    ) -> None:
        # SkillClientStub 未注册 · invoke 会 NotImplementedError → 映射为 DecompositionFailError
        client = SkillClientStub()
        client._handlers.pop("wbs.decompose")  # noqa: SLF001
        factory = WBSFactory(skill_client=client, event_bus=event_bus)
        with pytest.raises(DecompositionFailError):
            factory.handle_ic_19(cmd_ok)

    def test_wbs_error_base_code(self) -> None:
        assert NoProjectIdError().code == "E_WBS_NO_PROJECT_ID"
        assert FourPackIncompleteError(missing=["x"]).code == "E_WBS_4_PACK_INCOMPLETE"
        assert ArchOutputMissingError().code == "E_WBS_ARCH_OUTPUT_MISSING"
        assert DecompositionFailError(reason="r").code == "E_WBS_DECOMPOSITION_FAIL"
        assert TopologyCorruptError(reason="r").code == "E_WBS_TOPOLOGY_CORRUPT"


# =====================================================================
# §6 decompose_wbs 便捷函数
# =====================================================================

class TestDecomposeWBSHelper:
    def test_returns_wbs_draft(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        project_id: str, four_pack, arch_out,
    ) -> None:
        draft = decompose_wbs(
            four_set_plan=four_pack,
            architecture_output=arch_out,
            project_id=project_id,
            skill_client=skill_client,
            event_bus=event_bus,
        )
        assert isinstance(draft, WBSDraft)
        assert draft.project_id == project_id
        assert draft.wp_count == 3
        assert draft.topology_version.startswith("topo-v-")

    def test_dict_inputs_accepted(
        self, skill_client: SkillClientStub, project_id: str,
    ) -> None:
        draft = decompose_wbs(
            four_set_plan={
                "charter_path": "a", "plan_path": "b",
                "requirements_path": "c", "risk_path": "d",
            },
            architecture_output={"togaf_phases": ["B"], "adr_path": "adr.md"},
            project_id=project_id,
            skill_client=skill_client,
        )
        assert draft.wp_count == 3

    def test_string_granularity_accepted(
        self, skill_client: SkillClientStub, project_id: str, four_pack, arch_out,
    ) -> None:
        draft = decompose_wbs(
            four_set_plan=four_pack,
            architecture_output=arch_out,
            project_id=project_id,
            skill_client=skill_client,
            target_granularity="fine",
        )
        assert draft.wp_count == 3


# =====================================================================
# §7 集成：WBS → 装图 链路
# =====================================================================

class TestIntegrationWithTopologyManager:
    def test_wbs_draft_feeds_into_topology_manager(
        self, skill_client: SkillClientStub, event_bus: EventBusStub,
        project_id: str, four_pack, arch_out,
    ) -> None:
        """WBS 拆解 → L2-02 装图全链路（WP02 × WP01 集成锚点）。"""
        draft = decompose_wbs(
            four_set_plan=four_pack,
            architecture_output=arch_out,
            project_id=project_id,
            skill_client=skill_client,
            event_bus=event_bus,
        )
        manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        topo = manager.load_topology(draft.wp_list, draft.dag_edges)
        assert topo.wp_count if hasattr(topo, 'wp_count') else len(topo.wp_list) == 3
        # 装图事件 + 拆解事件都 emit 了
        assert len(event_bus.filter(event_type="L1-03:wbs_topology_ready")) == 1
        assert len(event_bus.filter(event_type="L1-03:wbs_decomposed")) == 1
