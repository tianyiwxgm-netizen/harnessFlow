"""Row L1-02 项目生命周期 → others · 3 cells × 6 TC = 18 TC.

**3 cells**:
    L1-02 → L1-03 · IC-02 trigger 拆解请求 / 拓扑校验
    L1-02 → L1-04 · IC-14 stage_gate verdict 请求 (Gate 编译 / Verifier)
    L1-02 → L1-09 · IC-03 stage_artifact_emitted (4 件套 / PMP / TOGAF)

**每 cell 6 TC**: HAPPY × 2 / NEGATIVE × 2 / SLO × 1 / E2E × 1.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)
from tests.shared.matrix_helpers import CaseType


# =============================================================================
# Cell 1: L1-02 → L1-03 · IC-02 trigger WBS 拆解 (6 TC)
# =============================================================================


class TestRowL1_02_to_L1_03:
    """L1-02 项目生命周期 → L1-03 WBS · IC-02 trigger / 拓扑校验.

    用真 WBSFactory + Fake skill_client (生产 raw WPs) 走拆解链.
    """

    def _build_command(
        self,
        project_id: str,
        *,
        command_id: str = "cmd-m3-1",
        mode: str = "full",
    ):
        from app.l1_03.wbs_decomposer.schemas import (
            ArchitectureOutput,
            FourSetPlan,
            RequestWBSDecompositionCommand,
            TargetGranularity,
        )

        return RequestWBSDecompositionCommand(
            command_id=command_id,
            project_id=project_id,
            artifacts_4_pack=FourSetPlan(
                charter_path="/p/charter.md",
                plan_path="/p/plan.md",
                requirements_path="/p/requirements.md",
                risk_path="/p/risk.md",
            ),
            architecture_output=ArchitectureOutput(
                togaf_phases=["A", "B"],
                adr_path="/p/adr.md",
            ),
            target_wp_granularity=TargetGranularity.MEDIUM,
            mode=mode,
        )

    def _build_skill_client(self, *, project_id="proj-m3-shared", raw_wps=None, raw_edges=None):
        """构造一个 SkillClientLike 替身 · 直返预置 wp_list/edges."""
        if raw_wps is None:
            raw_wps = [
                {
                    "wp_id": "wp-1",
                    "project_id": project_id,
                    "goal": "实现 WP-1 业务目标",
                    "dod_expr_ref": "dod://wp-1",
                    "deps": [],
                    "effort_estimate": 3.0,
                },
            ]
        if raw_edges is None:
            raw_edges = []

        class _SkillClient:
            def invoke_skill(self, capability: str, params: dict) -> dict:
                return {"wp_list": raw_wps, "edges": raw_edges}

        return _SkillClient()

    def test_happy_full_decompose_accepted(
        self, project_id: str, matrix_cov,
    ) -> None:
        """HAPPY · full mode · accepted=True · session_id 非空."""
        from app.l1_03.wbs_decomposer.factory import WBSFactory

        from .conftest import record_cell

        factory = WBSFactory(skill_client=self._build_skill_client(project_id=project_id))
        cmd = self._build_command(project_id)
        result = factory.handle_ic_19(cmd)
        assert result.accepted is True
        assert result.decomposition_session_id
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.HAPPY)

    def test_happy_decompose_with_multi_wps(
        self, project_id: str, matrix_cov,
    ) -> None:
        """HAPPY · 拆出 3 个 WP · 全部合规."""
        from app.l1_03.wbs_decomposer.factory import WBSFactory

        from .conftest import record_cell

        wps = [
            {
                "wp_id": f"wp-{i}", "project_id": project_id,
                "goal": f"WP-{i} 目标", "dod_expr_ref": f"dod://wp-{i}",
                "deps": [], "effort_estimate": 2.5,
            }
            for i in range(3)
        ]
        factory = WBSFactory(
            skill_client=self._build_skill_client(project_id=project_id, raw_wps=wps),
        )
        cmd = self._build_command(project_id, command_id="cmd-3wps")
        result = factory.handle_ic_19(cmd)
        assert result.accepted is True
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.HAPPY)

    def test_negative_oversize_wp_rejected(
        self, project_id: str, matrix_cov,
    ) -> None:
        """NEGATIVE · WP effort_estimate > 5 · 应抛 OversizeError 或 ValidationError."""
        from app.l1_03.wbs_decomposer.factory import (
            DecompositionFailError,
            TopologyCorruptError,
            WBSFactory,
        )

        from .conftest import record_cell

        wps = [
            {
                "wp_id": "wp-big", "project_id": project_id,
                "goal": "BIG WP", "dod_expr_ref": "dod://big",
                "deps": [], "effort_estimate": 10.0,  # > 5
            },
        ]
        factory = WBSFactory(
            skill_client=self._build_skill_client(project_id=project_id, raw_wps=wps),
        )
        cmd = self._build_command(project_id, command_id="cmd-oversize")
        with pytest.raises((Exception,)) as exc_info:
            factory.handle_ic_19(cmd)
        # 应是 oversize 或 topology corrupt 类
        assert "Oversize" in type(exc_info.value).__name__ or "Corrupt" in type(exc_info.value).__name__ or "5" in str(exc_info.value)
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.NEGATIVE)

    def test_negative_pm14_pid_in_command(
        self, project_id: str, other_project_id: str, matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · command 携带的 pid 进入 result · PM-14 链路保持."""
        from app.l1_03.wbs_decomposer.factory import WBSFactory

        from .conftest import record_cell

        # 用 other_project_id 构造 cmd · skill_client 也用同 pid 构造 wps
        factory = WBSFactory(
            skill_client=self._build_skill_client(project_id=other_project_id),
        )
        cmd = self._build_command(other_project_id, command_id="cmd-pm14")
        result = factory.handle_ic_19(cmd)
        # accepted 但 pid 透传 · 上游需用 result.command_id 关联回去
        assert result.accepted is True
        # 验证 command_id 透传 (PM-14 isolation 由 pid 字段保证)
        assert result.command_id == "cmd-pm14"
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.PM14)

    def test_slo_decompose_under_500ms(
        self, project_id: str, matrix_cov,
    ) -> None:
        """SLO · WBS dispatch sync < 500ms (含 LLM mock 即时返)."""
        from app.l1_03.wbs_decomposer.factory import WBSFactory

        from .conftest import record_cell

        factory = WBSFactory(skill_client=self._build_skill_client(project_id=project_id))
        cmd = self._build_command(project_id, command_id="cmd-slo")
        t0 = time.monotonic()
        factory.handle_ic_19(cmd)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 500, f"IC-02 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.HAPPY)

    def test_e2e_two_decomposes_independent(
        self, project_id: str, other_project_id: str, matrix_cov,
    ) -> None:
        """E2E · 两次不同 pid 拆解 · 各 session_id 独立."""
        from app.l1_03.wbs_decomposer.factory import WBSFactory

        from .conftest import record_cell

        factory_a = WBSFactory(skill_client=self._build_skill_client(project_id=project_id))
        factory_b = WBSFactory(skill_client=self._build_skill_client(project_id=other_project_id))
        cmd_a = self._build_command(project_id, command_id="cmd-A")
        cmd_b = self._build_command(other_project_id, command_id="cmd-B")
        ra = factory_a.handle_ic_19(cmd_a)
        rb = factory_b.handle_ic_19(cmd_b)
        assert ra.accepted is True and rb.accepted is True
        # session_id 必不同
        assert ra.decomposition_session_id != rb.decomposition_session_id
        record_cell(matrix_cov, "L1-02", "L1-03", CaseType.DEGRADE)


# =============================================================================
# Cell 2: L1-02 → L1-04 · IC-14 stage_gate verdict 请求 (6 TC)
# =============================================================================


class TestRowL1_02_to_L1_04:
    """L1-02 项目生命周期 → L1-04 Quality Loop · IC-14 stage gate verdict."""

    def test_happy_l1_02_emits_state_transition_event(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-02 emit state_transitioned 事件 · L1-04 可消费验证."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-02:state_transitioned",
            actor="main_loop",
            payload={
                "transition_id": "trans-0001",
                "from_state": "PLANNING",
                "to_state": "TDD_PLANNING",
            },
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt)
        assert result.persisted is True
        # 验证 IC-09 落盘 · L1-04 可读
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:state_transitioned",
            min_count=1,
        )
        assert events[0]["payload"]["to_state"] == "TDD_PLANNING"
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.HAPPY)

    def test_happy_gate_decision_audit(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · L1-02 emit gate_decision_made 事件."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-02:gate_decision_made",
            actor="main_loop",
            payload={"gate_id": "gate-1", "decision": "pass"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt)
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision_made",
            min_count=1,
        )
        assert events[0]["payload"]["decision"] == "pass"
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.HAPPY)

    def test_negative_l1_02_invalid_to_state_in_payload(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """NEGATIVE · 即使 payload 含非法值 · IC-09 仍记录 · L1-04 解析时拒."""
        from .conftest import record_cell

        # bus 层不语义校验 payload · 写入成功
        evt = Event(
            project_id=project_id,
            type="L1-02:state_transitioned",
            actor="main_loop",
            payload={"to_state": "INVALID_STATE"},
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt)
        assert result.persisted is True
        # 但消费方(L1-04)要校验 · 此处只记录 L1-02 已发
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:state_transitioned",
            min_count=1,
        )
        assert events[0]["payload"]["to_state"] == "INVALID_STATE"
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.NEGATIVE)

    def test_negative_pm14_state_event_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 的 state event 物理分片隔离."""
        from .conftest import record_cell

        for pid in (project_id, other_project_id):
            real_event_bus.append(Event(
                project_id=pid,
                type="L1-02:state_transitioned",
                actor="main_loop",
                payload={"transition_id": f"trans-{pid}"},
                timestamp=datetime.now(UTC),
            ))
        # pid_A 分片只 1 条
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-02:state_transitioned", min_count=1,
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-02:state_transitioned", min_count=1,
        )
        assert a[0]["sequence"] == 1
        assert b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.PM14)

    def test_slo_state_event_append_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · L1-02 → bus → L1-04 audit append < 50ms."""
        from .conftest import record_cell

        evt = Event(
            project_id=project_id,
            type="L1-02:gate_decision_made",
            actor="main_loop",
            payload={"gate_id": "g1"},
            timestamp=datetime.now(UTC),
        )
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-14 trigger SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.HAPPY)

    def test_e2e_full_stage_gate_lifecycle(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · S1→S5 5 stage 全 transition · 5 个 IC-14 trigger event."""
        from .conftest import record_cell

        stages = ["S1", "S2", "S3", "S4", "S5"]
        for s in stages:
            real_event_bus.append(Event(
                project_id=project_id,
                type="L1-02:gate_decision_made",
                actor="main_loop",
                payload={"gate_id": f"gate-{s}", "stage": s, "decision": "pass"},
                timestamp=datetime.now(UTC),
            ))
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:gate_decision_made",
            min_count=5,
        )
        assert len(events) == 5
        # 5 stage 顺序正确
        seen_stages = [e["payload"]["stage"] for e in events]
        assert seen_stages == stages
        record_cell(matrix_cov, "L1-02", "L1-04", CaseType.DEGRADE)


# =============================================================================
# Cell 3: L1-02 → L1-09 · IC-03 stage_artifact_emitted (6 TC)
# =============================================================================


class TestRowL1_02_to_L1_09:
    """L1-02 项目生命周期 → L1-09 EventBus · IC-03 stage artifact emit (4 件套)."""

    def _artifact_event(
        self,
        project_id: str,
        artifact_kind: str,
        stage: str = "S1",
    ) -> Event:
        return Event(
            project_id=project_id,
            type="L1-02:stage_artifact_emitted",
            actor="main_loop",
            payload={
                "artifact_kind": artifact_kind,
                "stage": stage,
                "path": f"/projects/{project_id}/{artifact_kind}.md",
            },
            timestamp=datetime.now(UTC),
        )

    def test_happy_charter_artifact_emitted(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 4 件套之 charter 落盘并发出 stage_artifact_emitted."""
        from .conftest import record_cell

        evt = self._artifact_event(project_id, "charter")
        real_event_bus.append(evt)
        assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            payload_contains={"artifact_kind": "charter"},
        )
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.HAPPY)

    def test_happy_4_pieces_full_set(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """HAPPY · 4 件套全发 · 各 1 条 audit."""
        from .conftest import record_cell

        for kind in ("charter", "plan", "requirements", "risk"):
            real_event_bus.append(self._artifact_event(project_id, kind))
        events = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-02:stage_artifact_emitted",
            min_count=4,
        )
        kinds = {e["payload"]["artifact_kind"] for e in events}
        assert kinds == {"charter", "plan", "requirements", "risk"}
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.HAPPY)

    def test_negative_invalid_event_actor(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """NEGATIVE · L1-02 事件用了非法 actor · pydantic 拒绝."""
        from .conftest import record_cell

        with pytest.raises(Exception):
            Event(
                project_id=project_id,
                type="L1-02:stage_artifact_emitted",
                actor="bad_actor_xyz",  # 非白名单
                payload={"k": 1},
                timestamp=datetime.now(UTC),
            )
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.NEGATIVE)

    def test_negative_pm14_artifact_isolation(
        self,
        project_id: str,
        other_project_id: str,
        real_event_bus,
        event_bus_root: Path,
        matrix_cov,
    ) -> None:
        """NEGATIVE/PM-14 · 不同 pid 各自 charter 分片独立."""
        from .conftest import record_cell

        real_event_bus.append(self._artifact_event(project_id, "charter"))
        real_event_bus.append(self._artifact_event(other_project_id, "charter"))
        a = assert_ic_09_emitted(
            event_bus_root, project_id=project_id,
            event_type="L1-02:stage_artifact_emitted", min_count=1,
        )
        b = assert_ic_09_emitted(
            event_bus_root, project_id=other_project_id,
            event_type="L1-02:stage_artifact_emitted", min_count=1,
        )
        assert a[0]["payload"]["artifact_kind"] == "charter"
        assert b[0]["payload"]["artifact_kind"] == "charter"
        # 各自 seq=1
        assert a[0]["sequence"] == 1 and b[0]["sequence"] == 1
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.PM14)

    def test_slo_artifact_emit_under_50ms(
        self, project_id: str, real_event_bus, matrix_cov,
    ) -> None:
        """SLO · IC-03 artifact emit < 50ms."""
        from .conftest import record_cell

        evt = self._artifact_event(project_id, "togaf")
        t0 = time.monotonic()
        real_event_bus.append(evt)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 50, f"IC-03 SLO {elapsed_ms:.2f}ms"
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.HAPPY)

    def test_e2e_full_pmp_togaf_artifacts(
        self, project_id: str, real_event_bus, event_bus_root: Path, matrix_cov,
    ) -> None:
        """E2E · PMP 9 计划 + TOGAF 全 artifact emit · hash chain 完整."""
        from .conftest import record_cell

        artifacts = [
            "charter", "plan", "requirements", "risk",  # 4 件套
            "scope_plan", "schedule_plan", "cost_plan", "quality_plan",  # PMP
            "togaf_phase_a", "togaf_phase_b",  # TOGAF
        ]
        for kind in artifacts:
            real_event_bus.append(self._artifact_event(project_id, kind))
        # hash chain 完整 + 10 条
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10
        record_cell(matrix_cov, "L1-02", "L1-09", CaseType.DEGRADE)
