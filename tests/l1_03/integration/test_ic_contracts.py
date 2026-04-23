"""ε-WP06 · IC-02 + IC-19 契约测试。

对齐 `docs/3-1-Solution-Technical/integration/ic-contracts.md §3.2 + §3.19`。
验证 schema 字段 / 类型 / 错误码覆盖。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.common.skill_client_stub import SkillClientStub
from app.l1_03.scheduler import (
    GetNextWPQuery,
    GetNextWPResult,
    WaitingReason,
    WPDispatcher,
)
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_03.wbs_decomposer import (
    ArchitectureOutput,
    FourSetPlan,
    RequestWBSDecompositionCommand,
    RequestWBSDecompositionResult,
    WBSFactory,
)

# ---------------------------------------------------------------------
# IC-02 contract
# ---------------------------------------------------------------------

class TestIC02ContractSchema:
    def test_query_required_fields(self, project_id: str) -> None:
        """ic-contracts §3.2.2：query_id / project_id / requester_tick 必带。"""
        schema = GetNextWPQuery.model_json_schema()
        required = set(schema.get("required", []))
        assert {"query_id", "project_id", "requester_tick"}.issubset(required)

    def test_result_has_3_state_fields(self) -> None:
        """ic-contracts §3.2.3：wp_id / deps_met / waiting_reason / in_flight_wp_count / topology_version。"""
        schema = GetNextWPResult.model_json_schema()
        props = set(schema.get("properties", {}).keys())
        assert {"wp_id", "deps_met", "waiting_reason",
                "in_flight_wp_count", "topology_version"}.issubset(props)

    def test_wp_id_nullable(self) -> None:
        """wp_id 必须是 nullable（类型是 str | null）。"""
        r = GetNextWPResult(
            query_id="q", wp_id=None, in_flight_wp_count=0, topology_version="v",
        )
        assert r.wp_id is None

    def test_prefer_critical_path_defaults_true(self, project_id: str) -> None:
        q = GetNextWPQuery(
            query_id="q", project_id=project_id, requester_tick="t",
        )
        assert q.prefer_critical_path is True

    def test_waiting_reason_enum_covers_all(self) -> None:
        """ic-contracts §3.2.3 waiting_reason 4 大类 · 加上 deadlock 共 5。"""
        vals = {str(x) for x in WaitingReason}
        assert {"all_done", "awaiting_deps", "concurrency_cap",
                "deadlock", "lock_contention"}.issubset(vals)


class TestIC02ErrorCodes:
    """验证 5 个错误码都有触达路径。"""

    def _mk_mgr(
        self, project_id: str, event_bus: EventBusStub,
        make_wp, num_wps: int = 3,
    ) -> WBSTopologyManager:
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        wps = [make_wp(f"wp-{i}") for i in range(num_wps)]
        mgr.load_topology(wps, [])
        return mgr

    def test_e_wp_cross_project(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        mgr = self._mk_mgr(project_id, event_bus, make_wp)
        d = WPDispatcher(mgr, event_bus)
        q = GetNextWPQuery(query_id="q", project_id="pid-ATTACKER", requester_tick="t")
        r = d.get_next_wp(q)
        assert r.error_code == "E_WP_CROSS_PROJECT"

    def test_e_wp_concurrency_cap(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        mgr = self._mk_mgr(project_id, event_bus, make_wp)
        mgr.transition_state("wp-0", State.READY, State.RUNNING)
        mgr.transition_state("wp-1", State.READY, State.RUNNING)
        d = WPDispatcher(mgr, event_bus)
        q = GetNextWPQuery(query_id="q", project_id=project_id, requester_tick="t")
        r = d.get_next_wp(q)
        assert r.error_code == "E_WP_CONCURRENCY_CAP"
        assert r.waiting_reason == WaitingReason.CONCURRENCY_CAP


# ---------------------------------------------------------------------
# IC-19 contract
# ---------------------------------------------------------------------

class TestIC19ContractSchema:
    def test_command_required_fields(self) -> None:
        schema = RequestWBSDecompositionCommand.model_json_schema()
        required = set(schema.get("required", []))
        assert {"command_id", "project_id", "artifacts_4_pack",
                "architecture_output"}.issubset(required)

    def test_result_has_accepted_and_session(self) -> None:
        schema = RequestWBSDecompositionResult.model_json_schema()
        required = set(schema.get("required", []))
        assert {"command_id", "accepted"}.issubset(required)

    def test_granularity_has_3_values(self) -> None:
        from app.l1_03.wbs_decomposer.schemas import TargetGranularity
        assert {str(x) for x in TargetGranularity} == {"fine", "medium", "coarse"}

    def test_mode_full_or_incremental(self, project_id: str) -> None:
        four = FourSetPlan(charter_path="a", plan_path="b",
                           requirements_path="c", risk_path="d")
        arch = ArchitectureOutput(togaf_phases=[], adr_path="adr.md")
        # full 模式默认
        cmd = RequestWBSDecompositionCommand(
            command_id="c", project_id=project_id,
            artifacts_4_pack=four, architecture_output=arch,
        )
        assert cmd.mode == "full"
        # incremental 模式
        cmd2 = RequestWBSDecompositionCommand(
            command_id="c2", project_id=project_id,
            artifacts_4_pack=four, architecture_output=arch,
            mode="incremental", target_wp_id="wp-x",
        )
        assert cmd2.mode == "incremental"

    def test_ic19_invalid_mode_rejected(self, project_id: str) -> None:
        four = FourSetPlan(charter_path="a", plan_path="b",
                           requirements_path="c", risk_path="d")
        arch = ArchitectureOutput(togaf_phases=[], adr_path="adr.md")
        with pytest.raises(ValidationError):
            RequestWBSDecompositionCommand(
                command_id="c", project_id=project_id,
                artifacts_4_pack=four, architecture_output=arch,
                mode="unknown_mode",  # type: ignore[arg-type]
            )


class TestIC19ErrorCodes:
    def test_e_wbs_decomposition_fail(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        from app.l1_03.wbs_decomposer.factory import DecompositionFailError
        skill = SkillClientStub()
        skill.register("wbs.decompose", lambda _p: (_ for _ in ()).throw(
            RuntimeError("llm down")))
        cmd = RequestWBSDecompositionCommand(
            command_id="c", project_id=project_id,
            artifacts_4_pack=FourSetPlan(
                charter_path="a", plan_path="b",
                requirements_path="c", risk_path="d",
            ),
            architecture_output=ArchitectureOutput(
                togaf_phases=[], adr_path="adr.md",
            ),
        )
        factory = WBSFactory(skill_client=skill, event_bus=event_bus)
        with pytest.raises(DecompositionFailError):
            factory.handle_ic_19(cmd)
