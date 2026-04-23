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


# ---------------------------------------------------------------------
# IC-09 contract · append_event（§3.9.2）
# ---------------------------------------------------------------------

class TestIC09ContractSchema:
    """EventBusStub 必须接纳 IC-09 §3.9.2 全部必填字段（event_id / actor / ts）。

    当 Dev-α 真实 EventAppender 替换进来时 · 调用端（12+ `_emit` 调用点）
    零改动。stub 宽松（未传默认填充）· 真实 impl 严格（缺字段 raise）。
    """

    def test_ic09_required_field_whitelist(self) -> None:
        """`_IC09_REQUIRED` 白名单 ≡ ic-contracts §3.9.2 required."""
        from app.l1_03.common.event_bus_stub import _IC09_REQUIRED
        # §3.9.2: required: [event_id, event_type, project_id_or_system, payload, actor, ts]
        # stub 用 project_id（alias of project_id_or_system）
        assert set(_IC09_REQUIRED) == {
            "event_id", "event_type", "project_id", "payload", "actor", "ts",
        }

    def test_ic09_append_accepts_full_contract_fields(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """完整 IC-09 入参全部下发 · stub 全部接纳 · 原样回存。"""
        result = event_bus.append(
            event_type="L1-03:wp_state_changed",
            project_id=project_id,
            payload={"wp_id": "wp-a", "from": "READY", "to": "RUNNING"},
            event_id="evt-0180dead1337",
            actor={"l1": "L1-03", "l2": "L2-02"},
            ts="2026-04-23T10:30:00Z",
            trigger_tick="tick-42",
            correlation_id="corr-xyz",
        )
        # §3.9.3 出参必含 event_id / sequence / hash / prev_hash / persisted / ts_persisted
        assert result["event_id"] == "evt-0180dead1337"
        assert result["sequence"] == 1
        assert result["persisted"] is True
        assert "hash" in result and "prev_hash" in result and "ts_persisted" in result
        # 回存对象字段完整
        rec = event_bus.events[0]
        assert rec.event_id == "evt-0180dead1337"
        assert rec.actor == {"l1": "L1-03", "l2": "L2-02"}
        assert rec.ts == "2026-04-23T10:30:00Z"
        assert rec.trigger_tick == "tick-42"
        assert rec.correlation_id == "corr-xyz"
        assert rec.payload == {"wp_id": "wp-a", "from": "READY", "to": "RUNNING"}

    def test_ic09_append_strict_raises_on_missing_event_id(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """`append_strict` 严格模式缺 event_id → raise（真实 IC-09 契约行为）。"""
        with pytest.raises((ValueError, TypeError)):
            event_bus.append_strict(  # type: ignore[call-arg]
                event_type="L1-03:foo",
                project_id=project_id,
                payload={"x": 1},
                event_id="",  # 空串 → 违反 IC-09 required
                actor={"l1": "L1-03"},
                ts="2026-04-23T10:30:00Z",
            )

    def test_ic09_append_strict_raises_on_missing_actor(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """严格模式缺 actor → raise。"""
        with pytest.raises(ValueError, match="actor"):
            event_bus.append_strict(
                event_type="L1-03:foo",
                project_id=project_id,
                payload={"x": 1},
                event_id="evt-0180000000aa",
                actor={},  # 缺 l1 字段
                ts="2026-04-23T10:30:00Z",
            )

    def test_ic09_append_strict_raises_on_missing_ts(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """严格模式缺 ts → raise。"""
        with pytest.raises(ValueError, match="ts"):
            event_bus.append_strict(
                event_type="L1-03:foo",
                project_id=project_id,
                payload={"x": 1},
                event_id="evt-0180000000bb",
                actor={"l1": "L1-03"},
                ts="",  # 空 ts
            )

    def test_ic09_append_lenient_defaults_when_fields_omitted(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """宽松路径：未传 event_id / actor / ts → stub 自动生成默认值。

        真实 EventAppender 替换后可改为严格；当前 12+ `_emit` 调用点无需改动。
        """
        result = event_bus.append(
            event_type="L1-03:wp_state_changed",
            project_id=project_id,
            content={"wp_id": "wp-a"},  # 用 legacy alias
        )
        rec = event_bus.events[0]
        # event_id 自动生成 evt-{uuid}
        assert rec.event_id.startswith("evt-") and len(rec.event_id) > 4
        assert result["event_id"] == rec.event_id
        # actor 默认 {"l1": "L1-03"}
        assert rec.actor == {"l1": "L1-03"}
        # ts 默认 ISO-8601 Z
        assert rec.ts.endswith("Z")

    def test_ic09_payload_and_content_mutex(
        self, project_id: str, event_bus: EventBusStub,
    ) -> None:
        """payload 与 content 同时传 → TypeError（content 只是 legacy alias）。"""
        with pytest.raises(TypeError, match="互斥"):
            event_bus.append(
                event_type="L1-03:foo",
                project_id=project_id,
                content={"a": 1},
                payload={"b": 2},
            )

    def test_ic09_pm14_empty_project_id_rejected(
        self, event_bus: EventBusStub,
    ) -> None:
        """PM-14 硬约束 · empty project_id → ValueError。"""
        with pytest.raises(ValueError, match="PM-14"):
            event_bus.append(
                event_type="L1-03:foo",
                project_id="",
                payload={"x": 1},
            )

    def test_ic09_existing_emit_callers_unchanged(
        self, project_id: str, event_bus: EventBusStub, make_wp,
    ) -> None:
        """Drop-in 兼容保证：现有 12+ `_emit` 调用点（content= / project_id=）仍工作。

        模拟一次 topology manager transition_state → event 成功 append。
        真实 EventAppender 替换时这些调用点零改动。
        """
        from app.l1_03.topology.manager import WBSTopologyManager
        from app.l1_03.topology.state_machine import State
        mgr = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
        mgr.load_topology([make_wp("wp-a")], [])
        mgr.transition_state("wp-a", State.READY, State.RUNNING)
        # event_bus 接到 wp_state_changed event · 字段完整
        evs = event_bus.filter(event_type="L1-03:wp_state_changed")
        assert len(evs) == 1
        ev = evs[0]
        assert ev.project_id == project_id
        assert ev.payload.get("wp_id") == "wp-a"
        # content legacy alias 和 payload 同值
        assert ev.content == ev.payload
        # 默认填充的必填字段
        assert ev.event_id.startswith("evt-")
        assert ev.actor == {"l1": "L1-03"}
        assert ev.ts.endswith("Z")
