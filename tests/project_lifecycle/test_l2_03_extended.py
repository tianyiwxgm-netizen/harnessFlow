"""L2-03 扩展测试 · query_artifact_refs + request_wbs_decomposition + 更多错误码 + IC。

对齐 3-2 TDD md §2/§3/§4：
  - TC-010 query_artifact_refs
  - TC-104 CROSS_REF_DEAD
  - TC-107 AC_FORMAT_VIOLATION
  - TC-110 ID_PATTERN_VIOLATION
  - TC-112 LLM_OUTPUT_EMPTY
  - TC-606 IC-19 request_wbs_decomposition
  - TC-607 IC-09 5 事件
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.four_set.errors import (
    E_AC_FORMAT_VIOLATION,
    E_CROSS_REF_DEAD,
    E_DEPENDENCY_CLOSURE_EMPTY,
    E_ID_PATTERN_VIOLATION,
    E_LLM_OUTPUT_EMPTY,
    E_REDO_OUT_OF_SCOPE,
    FourSetError,
)
from app.project_lifecycle.four_set.producer import FourPiecesProducer
from app.project_lifecycle.four_set.schemas import (
    FourSetContext,
    FourSetManifest,
    FourSetRequest,
    StructuredErr,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def pid() -> str:
    return "p_abcdefgh-1234-5678-9abc-def012345678"


def _setup_upstream(root: Path, pid: str) -> FourSetContext:
    base = root / "projects" / pid
    (base / "chart").mkdir(parents=True, exist_ok=True)
    (base / "chart" / "HarnessFlowGoal.md").write_text("# Goal", encoding="utf-8")
    (base / "chart" / "HarnessFlowPrdScope.md").write_text("# Scope", encoding="utf-8")
    return FourSetContext(
        charter_path=str(base / "chart" / "HarnessFlowGoal.md"),
        stakeholders_path=str(base / "chart" / "HarnessFlowPrdScope.md"),
        goal_anchor_hash="sha256:" + "0" * 64,
    )


def _default_skill() -> MagicMock:
    m = MagicMock()

    def _deleg(*, role, **kwargs):
        return {
            "requirements-analysis": {"items": [
                {"id": "REQ-001", "description": "x", "priority": "P0"},
            ]},
            "goals-writing": {"items": [
                {"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]},
            ]},
            "ac-scenario-writer": {"items": [
                {"id": "AC-001", "given": "g", "when": "w", "then": "t",
                 "linked_goal": "GOAL-001"},
            ]},
            "quality-audit": {"items": [
                {"id": "QS-001", "measurable_criteria": "x",
                 "verification_method": "e2e_test", "linked_ac": "AC-001"},
            ]},
        }[role]

    m.delegate_subagent.side_effect = _deleg
    return m


def _default_template() -> MagicMock:
    m = MagicMock()
    m.render_template = lambda **kw: MagicMock(
        output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\n# {kw['kind']}\nbody"
    )
    return m


def _make_req(pid: str, root: Path) -> FourSetRequest:
    ctx = _setup_upstream(root, pid)
    return FourSetRequest(
        project_id=pid, request_id="r1", stage="S2",
        context=ctx, caller_l2="L2-01",
    )


class TestL2_03_QueryAndWBS:

    def test_TC_L102_L203_010_query_artifact_refs(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """query_artifact_refs 在 assemble 后返 FourSetManifest。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        sut.assemble_four_set(_make_req(pid, tmp_project_root), project_root=str(tmp_project_root))
        result = sut.query_artifact_refs(pid, project_root=str(tmp_project_root))
        assert result is not None
        assert isinstance(result, FourSetManifest)
        assert len(result.docs) == 4

    def test_TC_L102_L203_010b_query_returns_none_when_not_assembled(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        result = sut.query_artifact_refs(pid, project_root=str(tmp_project_root))
        assert result is None

    def test_TC_L102_L203_606_ic_19_request_wbs_decomposition(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        bus = MagicMock()
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=bus,
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        manifest = resp.result
        payload = sut.request_wbs_decomposition(
            pid, manifest, trim_level="full",
            artifacts_4_pack={
                "charter_path": "charter.md", "plan_path": "plan.md",
                "requirements_path": "req.md", "risk_path": "risk.md",
            },
            architecture_output={
                "togaf_phases": ["A", "B"], "adr_path": "adr.md",
            },
        )
        assert payload["project_id"] == pid
        assert payload["command_id"].startswith("wbs-req-")
        assert payload["four_set_manifest"]["manifest_hash"]
        # 确认事件发出
        wbs_events = [
            c for c in bus.append_event.call_args_list
            if c.kwargs["event_type"] == "ic_19_request_wbs_decomposition"
        ]
        assert len(wbs_events) == 1


class TestL2_03_IC19_Payload:
    """IC-19 §3.19.2 payload 必填字段校验 · fix-2026-04-23 P2-01。

    §3.19.2 required: [command_id, project_id, artifacts_4_pack,
                       architecture_output]
    """

    @pytest.fixture
    def sut_and_manifest(self, pid: str, tmp_project_root: Path) -> tuple:
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        return sut, resp.result

    def test_TC_L102_L203_660_ic_19_command_id_uuid_format(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """§3.19.2 · command_id 格式 wbs-req-{uuid}."""
        sut, manifest = sut_and_manifest
        payload = sut.request_wbs_decomposition(
            pid, manifest,
            artifacts_4_pack={
                "charter_path": "c.md", "plan_path": "p.md",
                "requirements_path": "r.md", "risk_path": "risk.md",
            },
            architecture_output={"togaf_phases": ["A"], "adr_path": "adr.md"},
        )
        assert payload["command_id"].startswith("wbs-req-")
        # 去掉前缀剩 uuid
        uuid_part = payload["command_id"][len("wbs-req-"):]
        assert len(uuid_part) >= 32, f"command_id uuid too short: {uuid_part!r}"

    def test_TC_L102_L203_661_ic_19_command_id_unique(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """command_id 每次不同 · 非缓存同 pid 多次调用（§3.19.5 Non-idempotent）."""
        sut, manifest = sut_and_manifest
        kw = dict(
            artifacts_4_pack={
                "charter_path": "c.md", "plan_path": "p.md",
                "requirements_path": "r.md", "risk_path": "risk.md",
            },
            architecture_output={"togaf_phases": ["A"], "adr_path": "adr.md"},
        )
        p1 = sut.request_wbs_decomposition(pid, manifest, **kw)
        p2 = sut.request_wbs_decomposition(pid, manifest, **kw)
        assert p1["command_id"] != p2["command_id"]

    def test_TC_L102_L203_662_ic_19_artifacts_4_pack_required(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """§3.19.2 · artifacts_4_pack required 4 子字段 charter/plan/requirements/risk。"""
        sut, manifest = sut_and_manifest
        payload = sut.request_wbs_decomposition(
            pid, manifest,
            artifacts_4_pack={
                "charter_path": "projects/x/chart/a.md",
                "plan_path": "projects/x/pmp/scope.md",
                "requirements_path": "projects/x/four-set/requirements.md",
                "risk_path": "projects/x/pmp/risk.md",
            },
            architecture_output={"togaf_phases": ["A"], "adr_path": "adr.md"},
        )
        assert "artifacts_4_pack" in payload
        a4p = payload["artifacts_4_pack"]
        for k in ("charter_path", "plan_path", "requirements_path", "risk_path"):
            assert k in a4p, f"artifacts_4_pack missing {k}"

    def test_TC_L102_L203_663_ic_19_architecture_output_required(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """§3.19.2 · architecture_output required 子字段 togaf_phases / adr_path。"""
        sut, manifest = sut_and_manifest
        payload = sut.request_wbs_decomposition(
            pid, manifest,
            artifacts_4_pack={
                "charter_path": "c.md", "plan_path": "p.md",
                "requirements_path": "r.md", "risk_path": "risk.md",
            },
            architecture_output={
                "togaf_phases": ["B", "C", "D"],
                "adr_path": "projects/x/togaf/adr.md",
            },
        )
        assert "architecture_output" in payload
        arch = payload["architecture_output"]
        assert "togaf_phases" in arch
        assert "adr_path" in arch
        assert isinstance(arch["togaf_phases"], list)

    def test_TC_L102_L203_664_ic_19_ts_iso8601(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """§3.19.2 · ts ISO-8601 Z (non-required by schema but we emit for audit)."""
        sut, manifest = sut_and_manifest
        payload = sut.request_wbs_decomposition(
            pid, manifest,
            artifacts_4_pack={
                "charter_path": "c.md", "plan_path": "p.md",
                "requirements_path": "r.md", "risk_path": "risk.md",
            },
            architecture_output={"togaf_phases": ["A"], "adr_path": "adr.md"},
        )
        assert "ts" in payload
        assert "T" in payload["ts"]
        assert payload["ts"].endswith("Z")

    def test_TC_L102_L203_665_ic_19_reject_missing_artifacts_4_pack(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """artifacts_4_pack 缺字段 · raise（schema 校验）."""
        sut, manifest = sut_and_manifest
        with pytest.raises((ValueError, FourSetError)):
            sut.request_wbs_decomposition(
                pid, manifest,
                artifacts_4_pack={"charter_path": "c.md"},  # 缺 3 字段
                architecture_output={"togaf_phases": ["A"], "adr_path": "adr.md"},
            )

    def test_TC_L102_L203_666_ic_19_reject_missing_architecture_output(
        self, sut_and_manifest, pid: str,
    ) -> None:
        """architecture_output 缺字段 · raise。"""
        sut, manifest = sut_and_manifest
        with pytest.raises((ValueError, FourSetError)):
            sut.request_wbs_decomposition(
                pid, manifest,
                artifacts_4_pack={
                    "charter_path": "c.md", "plan_path": "p.md",
                    "requirements_path": "r.md", "risk_path": "risk.md",
                },
                architecture_output={"adr_path": "adr.md"},  # 缺 togaf_phases
            )


class TestL2_03_MoreErrorCodes:

    def test_TC_L102_L203_112_llm_output_empty(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """skill 返 empty items · E_LLM_OUTPUT_EMPTY。"""
        empty_skill = MagicMock()
        empty_skill.delegate_subagent.return_value = {"items": []}
        sut = FourPiecesProducer(
            template=_default_template(), skill=empty_skill, event_bus=MagicMock(),
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        assert resp.status == "err"
        assert isinstance(resp.result, StructuredErr)
        assert resp.result.err_type == E_LLM_OUTPUT_EMPTY

    def test_TC_L102_L203_110_id_pattern_violation(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """LLM 返 id='REQ1'（非 REQ-\\d{3} pattern）· E_ID_PATTERN_VIOLATION。"""
        bad_skill = MagicMock()
        bad_skill.delegate_subagent.side_effect = lambda **kw: {
            "items": [{"id": "REQ1", "description": "x", "priority": "P0"}],
        }
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad_skill, event_bus=MagicMock(),
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        assert resp.status == "err"
        assert resp.result.err_type == E_ID_PATTERN_VIOLATION

    def test_TC_L102_L203_107_ac_format_violation(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """LLM 返 AC 缺 'when' 字段 · E_AC_FORMAT_VIOLATION。"""
        skill = MagicMock()

        def _deleg(*, role, **kwargs):
            return {
                "requirements-analysis": {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]},
                "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
                "ac-scenario-writer": {"items": [
                    {"id": "AC-001", "given": "g", "when": "", "then": "t",  # when 空
                     "linked_goal": "GOAL-001"},
                ]},
                "quality-audit": {"items": [
                    {"id": "QS-001", "measurable_criteria": "x",
                     "verification_method": "e2e_test", "linked_ac": "AC-001"},
                ]},
            }[role]

        skill.delegate_subagent.side_effect = _deleg
        sut = FourPiecesProducer(
            template=_default_template(), skill=skill, event_bus=MagicMock(),
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        assert resp.status == "err"
        assert resp.result.err_type == E_AC_FORMAT_VIOLATION


class TestL2_03_IcAndEvents:

    def test_TC_L102_L203_607_ic_09_5_events_sequence(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """IC-09 发 5 事件：requirements_ready / goals_ready / ac_ready / quality_ready / 4_pieces_ready。"""
        bus = MagicMock()
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=bus,
        )
        sut.assemble_four_set(_make_req(pid, tmp_project_root), project_root=str(tmp_project_root))
        events = [c.kwargs["event_type"] for c in bus.append_event.call_args_list]
        expected = [
            "requirements_ready", "goals_ready", "ac_ready", "quality_ready",
            "4_pieces_ready",
        ]
        for e in expected:
            assert e in events, f"missing event: {e}"
        # 相对顺序
        indices = [events.index(e) for e in expected]
        assert indices == sorted(indices), f"events out of order: {events}"

    def test_TC_L102_L203_603_ic_l2_02_render_template_called_4_times(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """IC-L2-02 · render_template 被调 4 次（4 doc_type 各 1 次）+ manifest 1 次 = 5 次 · caller_l2=L2-03。"""
        template = _default_template()
        template.render_template = MagicMock(side_effect=lambda **kw: MagicMock(
            output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\n# body"
        ))
        sut = FourPiecesProducer(
            template=template, skill=_default_skill(), event_bus=MagicMock(),
        )
        sut.assemble_four_set(_make_req(pid, tmp_project_root), project_root=str(tmp_project_root))
        calls = template.render_template.call_args_list
        assert len(calls) == 4
        kinds = [c.kwargs["kind"] for c in calls]
        assert kinds == [
            "fourset.requirements", "fourset.goals",
            "fourset.acceptance_criteria", "fourset.quality_standards",
        ]
        for c in calls:
            assert c.kwargs["caller_l2"] == "L2-03"

    def test_TC_L102_L203_604_ic_05_delegate_subagent_called_4_times(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """IC-05 · 4 role delegate 各 1 次。"""
        skill = _default_skill()
        sut = FourPiecesProducer(
            template=_default_template(), skill=skill, event_bus=MagicMock(),
        )
        sut.assemble_four_set(_make_req(pid, tmp_project_root), project_root=str(tmp_project_root))
        roles = [c.kwargs["role"] for c in skill.delegate_subagent.call_args_list]
        assert roles == [
            "requirements-analysis", "goals-writing",
            "ac-scenario-writer", "quality-audit",
        ]


# ---------------------------------------------------------------------------
# P2-04 fix-2026-04-23 · WP03 补 15 TC · 3 错误码各 5 TC（正/负/边界）
# 对齐 docs/3-1-Solution-Technical/L1-02-项目生命周期编排/L2-03-4 件套生产器.md
#   §5.2 E04 CROSS_REF_DEAD · E09 REDO_OUT_OF_SCOPE · E14 DEPENDENCY_CLOSURE_EMPTY
#   §6.3 cross_ref_check · §6.4 resolve_dependency_closure
# ---------------------------------------------------------------------------


def _redo_skill_with_deleted_req(deleted_id: str = "REQ-002") -> MagicMock:
    """Redo skill · 模拟 REQ-002 在重做中被删除 · goals 仍引用它。"""
    m = MagicMock()

    def _deleg(*, role, **kwargs):
        if role == "requirements-analysis":
            # 重做后只保留 REQ-001 · REQ-002 被删
            return {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]}
        if role == "goals-writing":
            # 仍引用已删的 REQ-002
            return {"items": [{
                "id": "GOAL-001", "statement": "x",
                "linked_reqs": ["REQ-001", deleted_id],  # dead ref
            }]}
        if role == "ac-scenario-writer":
            return {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-001",
            }]}
        if role == "quality-audit":
            return {"items": [{
                "id": "QS-001", "measurable_criteria": "x",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]}
        return {"items": []}

    m.delegate_subagent.side_effect = _deleg
    return m


class TestL2_03_E_CROSS_REF_DEAD:
    """E_CROSS_REF_DEAD (E04) · 5 TC · 下游引用上游已删 id（重做场景）。

    与 E_TRACEABILITY_BROKEN (E03) 区分:
      - E03 初始装配时 · cross_ref 整体失败
      - E04 重做场景 · 上游 id 被删 · 下游仍引 · 级联重做触发条件
    """

    def test_TC_L102_L203_801_cross_ref_dead_goal_to_deleted_req(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · redo=True · goal 引用被删 REQ-002 · E_CROSS_REF_DEAD。"""
        # 先 baseline assemble
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        # 再 redo · 上游删 REQ-002 · goal 仍 linked
        sut = FourPiecesProducer(
            template=_default_template(), skill=_redo_skill_with_deleted_req("REQ-002"),
            event_bus=MagicMock(),
        )
        ctx = _setup_upstream(tmp_project_root, pid)
        req = FourSetRequest(
            project_id=pid, request_id="redo-1", stage="S2",
            context=ctx, caller_l2="L2-01",
            target_subset=("requirements",),  # redo 信号
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_CROSS_REF_DEAD

    def test_TC_L102_L203_802_cross_ref_dead_ac_to_deleted_goal(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · redo · AC 引已删 GOAL-99 · E_CROSS_REF_DEAD。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        bad = MagicMock()
        bad.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-99",  # 上游已删
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "x",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad, event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="redo-2", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("goals",),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_CROSS_REF_DEAD

    def test_TC_L102_L203_803_cross_ref_dead_initial_assembly_uses_e03_not_e04(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """负 · 初始装配(无 target_subset)时 · 仍用 E_TRACEABILITY_BROKEN (E03)。"""
        from app.project_lifecycle.four_set.errors import E_TRACEABILITY_BROKEN
        bad = MagicMock()
        bad.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-99",
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "x",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad, event_bus=MagicMock(),
        )
        # 初始装配 · 无 target_subset
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        assert resp.status == "err"
        assert resp.result.err_type == E_TRACEABILITY_BROKEN

    def test_TC_L102_L203_804_cross_ref_dead_qs_to_deleted_ac(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · redo · QS 引已删 AC-99 · E_CROSS_REF_DEAD。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        bad = MagicMock()
        bad.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-001",
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "x",
                "verification_method": "e2e_test",
                "linked_ac": "AC-99",  # 上游 AC-99 已删
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad, event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="redo-3", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("acceptance_criteria",),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_CROSS_REF_DEAD

    def test_TC_L102_L203_805_cross_ref_dead_report_contains_dead_ref_info(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · dead_refs 在 StructuredErr.context 中列出 · 审计可追溯。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        sut = FourPiecesProducer(
            template=_default_template(),
            skill=_redo_skill_with_deleted_req("REQ-002"),
            event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="redo-4", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("requirements",),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_CROSS_REF_DEAD
        # context 含 dead_refs 明细
        assert "dead_refs" in resp.result.context or "errors" in resp.result.context
        ctx_str = str(resp.result.context)
        assert "REQ-002" in ctx_str  # 被删的 id 出现在审计信息中


class TestL2_03_E_DEPENDENCY_CLOSURE_EMPTY:
    """E_DEPENDENCY_CLOSURE_EMPTY (E14) · 5 TC · target_subset 解析空闭包。"""

    def test_TC_L102_L203_811_closure_empty_illegal_doc_type(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · target_subset 含非法 doc_type · E_DEPENDENCY_CLOSURE_EMPTY。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-closure-1", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("invalid_doc_type",),  # type: ignore[arg-type]
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_DEPENDENCY_CLOSURE_EMPTY

    def test_TC_L102_L203_812_closure_empty_returns_legal_list_in_context(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · 错误返回 context 含合法 doc_type 列表（§5.2 处理策略：返合法列表）。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-closure-2", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("typo_xxx",),  # type: ignore[arg-type]
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        # context 列出合法值
        ctx_str = str(resp.result.context)
        assert "requirements" in ctx_str
        assert "goals" in ctx_str

    def test_TC_L102_L203_813_closure_empty_single_valid_doc_type(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """负 · target_subset=("requirements",) · 合法闭包（含 4 项）· 不触发 E14。

        §6.4 CLOSURE['requirements'] = 4 项级联·合法。
        """
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-closure-3", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("requirements",),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "ok"

    def test_TC_L102_L203_814_closure_empty_target_subset_all_four(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · target_subset=全 4 · 合法闭包 · 不触发 E14。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-closure-4", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=(
                "requirements", "goals", "acceptance_criteria", "quality_standards",
            ),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "ok"

    def test_TC_L102_L203_815_closure_empty_mixed_valid_and_invalid(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · target_subset 含 1 合法 + 1 非法 · 必须 raise E14（严格校验）。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-closure-5", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("goals", "bogus"),  # type: ignore[arg-type]
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_DEPENDENCY_CLOSURE_EMPTY


class TestL2_03_E_REDO_OUT_OF_SCOPE:
    """E_REDO_OUT_OF_SCOPE (E09) · 5 TC · 重做越界修改。

    §5.2 内部 bug 安全网:
      redo 声称只改 target_subset + closure · 实际越界修改 · raise E09。
    """

    def test_TC_L102_L203_821_redo_out_of_scope_target_quality_only(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · target_subset=('quality_standards',) · closure={qs} · 但 skill 同时动了 REQ。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        # skill 声称只改 QS · 但实际也改了 REQ（返回不同 REQ-002）· 越界
        out_of_scope = MagicMock()
        out_of_scope.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [
                {"id": "REQ-001", "description": "x", "priority": "P0"},
                {"id": "REQ-002", "description": "new", "priority": "P0"},  # 新增 · 越界
            ]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-001",
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "new",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=out_of_scope, event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-scope-1", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("quality_standards",),  # closure 只 qs
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_REDO_OUT_OF_SCOPE

    def test_TC_L102_L203_822_redo_out_of_scope_context_mentions_offending_doc(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """正 · 错误 context 含越界 doc_type 明细（审计）。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        bad = MagicMock()
        bad.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [
                {"id": "REQ-001", "description": "x", "priority": "P0"},
                {"id": "REQ-002", "description": "out", "priority": "P0"},
            ]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-001",
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "n",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad, event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-scope-2", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("quality_standards",),
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        # context 点明越界 doc_type
        ctx_str = str(resp.result.context)
        assert "requirements" in ctx_str or "out_of_scope" in ctx_str

    def test_TC_L102_L203_823_redo_in_scope_no_error(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """负 · 重做 closure 内（target=req · closure 全 4）· 不触发 E09。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        # 重做 requirements · closure=全 4 · skill 修改任何 4 doc 都 in-scope
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-scope-3", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("requirements",),  # closure 含全 4 (§6.4)
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "ok"

    def test_TC_L102_L203_824_redo_ac_scope_rejects_req_change(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · target=ac · closure={ac,qs} · 修 req → E09。"""
        first = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        first.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        bad = MagicMock()
        bad.delegate_subagent.side_effect = lambda *, role, **kw: {
            "requirements-analysis": {"items": [
                {"id": "REQ-001", "description": "x", "priority": "P0"},
                {"id": "REQ-003", "description": "sneaky add", "priority": "P1"},
            ]},
            "goals-writing": {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]},
            "ac-scenario-writer": {"items": [{
                "id": "AC-001", "given": "g", "when": "w", "then": "t",
                "linked_goal": "GOAL-001",
            }]},
            "quality-audit": {"items": [{
                "id": "QS-001", "measurable_criteria": "x",
                "verification_method": "e2e_test", "linked_ac": "AC-001",
            }]},
        }[role]
        sut = FourPiecesProducer(
            template=_default_template(), skill=bad, event_bus=MagicMock(),
        )
        req = FourSetRequest(
            project_id=pid, request_id="r-scope-4", stage="S2",
            context=_setup_upstream(tmp_project_root, pid), caller_l2="L2-01",
            target_subset=("acceptance_criteria",),  # closure={ac,qs} · req 越界
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert resp.result.err_type == E_REDO_OUT_OF_SCOPE

    def test_TC_L102_L203_825_redo_out_of_scope_only_detects_in_redo_mode(
        self, pid: str, tmp_project_root: Path,
    ) -> None:
        """边界 · 初始装配(no target_subset) · 改任何 doc 都不是 redo · 不触发 E09。"""
        sut = FourPiecesProducer(
            template=_default_template(), skill=_default_skill(), event_bus=MagicMock(),
        )
        resp = sut.assemble_four_set(
            _make_req(pid, tmp_project_root), project_root=str(tmp_project_root),
        )
        # 初始路径 · 必须 ok
        assert resp.status == "ok"
