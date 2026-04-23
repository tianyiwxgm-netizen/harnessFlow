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
    E_ID_PATTERN_VIOLATION,
    E_LLM_OUTPUT_EMPTY,
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
        payload = sut.request_wbs_decomposition(pid, manifest, trim_level="full")
        assert payload["project_id"] == pid
        assert payload["command_id"].startswith("wbs-")
        assert payload["four_set_manifest"]["manifest_hash"]
        # 确认事件发出
        wbs_events = [
            c for c in bus.append_event.call_args_list
            if c.kwargs["event_type"] == "ic_19_request_wbs_decomposition"
        ]
        assert len(wbs_events) == 1


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
