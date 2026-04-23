"""L2-07 IC 契约集成测试 · §4 对齐 3-2 TDD md §4。

本 L2 被 5 个上游（L2-02/03/04/05/06）通过 IC-L2-02 调用 · 下游发 IC-09 2 类事件。
7 TC：TC-601~607。
"""
from __future__ import annotations

from typing import Any

import pytest

from app.project_lifecycle.template_engine.engine import TemplateEngine


@pytest.fixture
def sut(template_dir_real, mock_event_bus) -> TemplateEngine:
    return TemplateEngine.load_from_dir(
        template_dir=str(template_dir_real),
        event_emitter=mock_event_bus,
    )


def _minimal_slots_for(kind: str) -> dict[str, Any]:
    """按 kind 返最小合法 slots（对齐 templates/*/slot_schema required）。"""
    table: dict[str, dict[str, Any]] = {
        "kickoff.goal": {"user_utterance": "x", "goals": ["g"], "deadline": "2026-06-30"},
        "kickoff.scope": {"scope_items": ["a"], "out_of_scope": [], "constraints": []},
        "fourset.scope": {"scope_statement": "x", "in_scope": ["a"], "out_of_scope": []},
        "fourset.prd": {"problem_statement": "x", "success_metrics": [], "user_stories": []},
        "fourset.plan": {"milestones": [], "risks": []},
        "fourset.tdd": {"layers": [], "quality_gates": []},
        "pmp.integration": {"integration_summary": "x", "change_control": []},
        "pmp.scope": {"scope_statement": "x", "scope_items": [], "out_of_scope": []},
        "pmp.schedule": {"milestones": [], "critical_path": []},
        "pmp.cost": {"budget_total": 100000, "cost_breakdown": []},
        "pmp.quality": {"quality_objectives": [], "quality_checks": []},
        "pmp.resource": {"roles": [], "availability": []},
        "pmp.communication": {"channels": [], "cadence": []},
        "pmp.risk": {"risks": []},
        "pmp.procurement": {"items": []},
        "togaf.preliminary": {"principles": [], "stakeholders": []},
        "togaf.phase_a": {"vision": "x", "goals": []},
        "togaf.phase_b": {"business_capabilities": [], "value_streams": []},
        "togaf.phase_c_data": {"data_entities": [], "data_flows": []},
        "togaf.phase_c_application": {"applications": [], "interactions": []},
        "togaf.phase_d": {"tech_components": [], "standards": []},
        "togaf.phase_e": {"opportunities": [], "solutions": []},
        "togaf.phase_f": {"work_packages": []},
        "togaf.phase_g": {"governance_items": []},
        "togaf.phase_h": {"change_requests": []},
        "togaf.adr": {
            "title": "x", "context": "y", "decision": "z",
            "alternatives": [], "consequences": [],
        },
        "closing.lessons_learned": {
            "what_went_well": [], "what_went_wrong": [], "action_items": [],
        },
        "closing.delivery_manifest": {"deliverables": [], "checksums": []},
        "closing.retro_summary": {"summary": "x", "metrics": {"m1": 1}},
    }
    return table[kind]


class TestL2_07_IcContracts:
    """IC-L2-02（5 上游被调） + IC-09（下游生产） 契约 join test。"""

    def test_TC_L102_L207_601_ic_l2_02_called_by_L2_02_kickoff(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-L2-02 · L2-02 启动阶段 · kickoff.goal + kickoff.scope 契约。"""
        for kind in ("kickoff.goal", "kickoff.scope"):
            out = sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind=kind, slots=_minimal_slots_for(kind), caller_l2="L2-02",
            )
            assert out.request_id == mock_request_id
            assert out.template_id.startswith(f"{kind}.")
            assert out.template_version == "v1.0"

    def test_TC_L102_L207_602_ic_l2_02_called_by_L2_03_fourset(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-L2-02 · L2-03 4 件套（scope/prd/plan/tdd）。"""
        for kind in ("fourset.scope", "fourset.prd", "fourset.plan", "fourset.tdd"):
            out = sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind=kind, slots=_minimal_slots_for(kind), caller_l2="L2-03",
            )
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_603_ic_l2_02_called_by_L2_04_pmp_9_kdas(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-L2-02 · L2-04 PMP 9 kda 全部可渲。"""
        kdas = [
            "integration", "scope", "schedule", "cost", "quality",
            "resource", "communication", "risk", "procurement",
        ]
        for kda in kdas:
            kind = f"pmp.{kda}"
            out = sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind=kind, slots=_minimal_slots_for(kind), caller_l2="L2-04",
            )
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_604_ic_l2_02_called_by_L2_05_togaf_phases(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-L2-02 · L2-05 TOGAF 11 Phase + adr。"""
        phases = [
            "preliminary", "phase_a", "phase_b", "phase_c_data",
            "phase_c_application", "phase_d", "phase_e", "phase_f",
            "phase_g", "phase_h", "adr",
        ]
        for ph in phases:
            kind = f"togaf.{ph}"
            out = sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind=kind, slots=_minimal_slots_for(kind), caller_l2="L2-05",
            )
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_605_ic_l2_02_called_by_L2_06_closing(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-L2-02 · L2-06 收尾 3 模板。"""
        for kind in (
            "closing.lessons_learned",
            "closing.delivery_manifest",
            "closing.retro_summary",
        ):
            out = sut.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind=kind, slots=_minimal_slots_for(kind), caller_l2="L2-06",
            )
            assert out.template_id.startswith(f"{kind}.")

    def test_TC_L102_L207_606_ic_09_template_rendered_event_shape(
        self, sut: TemplateEngine, mock_project_id: str, mock_request_id: str,
        mock_event_bus: Any,
    ) -> None:
        """IC-09 append_event · template_rendered payload 契约（对齐 tech §7.5）。"""
        sut.render_template(
            request_id=mock_request_id, project_id=mock_project_id,
            kind="kickoff.goal", slots=_minimal_slots_for("kickoff.goal"),
            caller_l2="L2-02",
        )
        events = mock_event_bus.emitted_events()
        evt = next(e for e in events if e["event_type"] == "L1-02/L2-07:template_rendered")
        # tech §7.5 必填字段
        for field in (
            "project_id", "template_id", "template_version", "caller_l2",
            "slots_hash", "output_sha256", "rendered_at", "engine_version",
        ):
            assert field in evt, f"missing audit field: {field}"
        assert evt["caller_l2"] == "L2-02"
        assert evt["severity"] == "INFO"

    def test_TC_L102_L207_607_ic_09_critical_template_code_exec_event_shape(
        self, tmp_path, mock_project_id: str, mock_request_id: str,
    ) -> None:
        """IC-09 CRITICAL event · sandbox 拦截时 template_code_exec_attempt 事件契约。"""
        from app.project_lifecycle.common.event_emitter import EventEmitter
        from app.project_lifecycle.template_engine.errors import TemplateEngineError

        bus = EventEmitter()
        # 建含恶意模板的独立 engine
        mal_dir = tmp_path / "mal"
        (mal_dir / "mal").mkdir(parents=True)
        (mal_dir / "mal" / "x.md").write_text(
            "---\nkind: malicious.escape\nversion: v1.0\n"
            "slot_schema: {type: object, required: [x], properties: {x: {type: string}}}\n"
            "description: test\nauthor: t\ncreated_at: 2026-04-23\n---\n"
            "{{ x.__class__.__mro__[1].__subclasses__() }}\n",
            encoding="utf-8",
        )
        eng = TemplateEngine.load_from_dir(
            template_dir=str(mal_dir),
            event_emitter=bus,
            required_kinds=["malicious.escape"],
        )
        with pytest.raises(TemplateEngineError):
            eng.render_template(
                request_id=mock_request_id, project_id=mock_project_id,
                kind="malicious.escape", slots={"x": "y"}, caller_l2="L2-04",
            )
        crit = [
            e for e in bus.emitted_events()
            if e["event_type"] == "L1-02/L2-07:template_code_exec_attempt"
        ]
        assert len(crit) == 1
        evt = crit[0]
        assert evt["severity"] == "CRITICAL"
        assert evt["caller_l2"] == "L2-04"
        assert "sandbox_violation_type" in evt
