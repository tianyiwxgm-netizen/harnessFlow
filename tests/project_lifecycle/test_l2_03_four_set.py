"""L2-03 4 件套生产器测试 · 对齐 3-2 TDD md §2/§3。

TC 精选核心场景：
- TC-001 happy path full
- TC-003 串行 4 步顺序（REQ → GOAL → AC → QS）
- TC-004 总事件 4_pieces_ready
- TC-006~009 4 子步分别产出正确 doc_id 模式
- TC-101 UPSTREAM_MISSING
- TC-106 PM14_PID_MISMATCH
- TC-103/104 TRACEABILITY_BROKEN / CROSS_REF_DEAD
- TC-607 IC-09 5 事件
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.four_set.errors import (
    E_CROSS_REF_DEAD,
    E_PM14_PID_MISMATCH,
    E_TRACEABILITY_BROKEN,
    E_UPSTREAM_MISSING,
    FourSetError,
)
from app.project_lifecycle.four_set.producer import FourPiecesProducer
from app.project_lifecycle.four_set.schemas import (
    FourSetContext,
    FourSetManifest,
    FourSetRequest,
    FourSetResponse,
    StructuredErr,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def mock_pid() -> str:
    # 遵循 L2-02 pid 格式 p_{uuid-v4}
    return "p_12345678-1234-5678-9abc-def012345678"


def _setup_upstream(root: Path, pid: str) -> FourSetContext:
    """mock upstream：写 L2-02 章程 + manifest（模拟 S1 已完成）。"""
    base = root / "projects" / pid
    (base / "chart").mkdir(parents=True, exist_ok=True)
    (base / "meta").mkdir(parents=True, exist_ok=True)
    (base / "four-set").mkdir(parents=True, exist_ok=True)
    (base / "chart" / "HarnessFlowGoal.md").write_text(
        "---\ntemplate_id: kickoff.goal\n---\n# Goal\nbody", encoding="utf-8",
    )
    (base / "chart" / "HarnessFlowPrdScope.md").write_text(
        "---\ntemplate_id: kickoff.scope\n---\n# Scope\nbody", encoding="utf-8",
    )
    manifest = {"project_id": pid, "goal_anchor_hash": "sha256:" + "a" * 64}
    (base / "meta" / "project_manifest.yaml").write_text(
        json.dumps(manifest), encoding="utf-8",
    )
    return FourSetContext(
        charter_path=str(base / "chart" / "HarnessFlowGoal.md"),
        stakeholders_path=str(base / "chart" / "HarnessFlowPrdScope.md"),
        goal_anchor_hash="sha256:" + "a" * 64,
        project_manifest_path=str(base / "meta" / "project_manifest.yaml"),
    )


@pytest.fixture
def mock_template() -> MagicMock:
    """L2-07 TemplateEngine mock · render_template 4 次分别返 4 doc body。"""
    m = MagicMock()

    def _render(*, request_id, project_id, kind, slots, caller_l2):
        return MagicMock(
            output=f"---\ntemplate_id: {kind}.v1.0\ndoc_type: {kind.split('.')[-1]}\n---\n# {kind}\nbody",
            template_id=f"{kind}.v1.0",
            body_sha256="a" * 64,
        )

    m.render_template.side_effect = _render
    return m


@pytest.fixture
def mock_skill() -> MagicMock:
    """L1-05 skill delegate_subagent mock · 返 4 doc 结构化 items。"""
    m = MagicMock()

    def _delegate(*, project_id, delegation_id, role, task_brief, context_copy, **kwargs):
        if role == "requirements-analysis":
            return {
                "items": [
                    {"id": "REQ-001", "description": "authentication", "priority": "P0"},
                    {"id": "REQ-002", "description": "article CRUD", "priority": "P0"},
                ],
            }
        if role == "goals-writing":
            return {
                "items": [
                    {"id": "GOAL-001", "statement": "launch MVP",
                     "linked_reqs": ["REQ-001", "REQ-002"]},
                ],
            }
        if role == "ac-scenario-writer":
            return {
                "items": [
                    {"id": "AC-001",
                     "given": "user with creds", "when": "login",
                     "then": "session issued", "linked_goal": "GOAL-001"},
                ],
            }
        if role == "quality-audit":
            return {
                "items": [
                    {"id": "QS-001",
                     "measurable_criteria": "login P95 < 200ms",
                     "verification_method": "e2e_test",
                     "linked_ac": "AC-001"},
                ],
            }
        return {"items": []}

    m.delegate_subagent.side_effect = _delegate
    return m


@pytest.fixture
def mock_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_template, mock_skill, mock_event_bus) -> FourPiecesProducer:
    return FourPiecesProducer(
        template=mock_template,
        skill=mock_skill,
        event_bus=mock_event_bus,
    )


def _make_req(pid: str, root: Path, **overrides) -> FourSetRequest:
    ctx = _setup_upstream(root, pid)
    base = dict(
        project_id=pid,
        request_id="fs-req-001",
        stage="S2",
        context=ctx,
        trim_level="full",
        caller_l2="L2-01",
    )
    base.update(overrides)
    return FourSetRequest(**base)


class TestL2_03_FourSet_HappyPath:
    """正向 · happy path 全装配。"""

    def test_TC_L102_L203_001_assemble_full_success(
        self, sut: FourPiecesProducer,
        mock_pid: str, tmp_project_root: Path,
    ) -> None:
        """full 全量装配 · 返 FourSetManifest v1 · 4 doc paths 齐。"""
        req = _make_req(mock_pid, tmp_project_root)
        resp: FourSetResponse = sut.assemble_four_set(
            req, project_root=str(tmp_project_root),
        )
        assert resp.status == "ok"
        assert isinstance(resp.result, FourSetManifest)
        assert resp.result.version == "v1"
        assert set(resp.result.docs.keys()) == {
            "requirements", "goals", "acceptance_criteria", "quality_standards",
        }
        # 4 文件落盘
        for doc_type, doc_ref in resp.result.docs.items():
            assert Path(doc_ref.path).exists(), f"missing {doc_type}"
        # cross_check 无错
        assert resp.result.cross_check_report.errors == ()

    def test_TC_L102_L203_003_four_steps_serial_order(
        self, sut: FourPiecesProducer, mock_pid: str, tmp_project_root: Path,
        mock_event_bus: MagicMock,
    ) -> None:
        """4 步严格 REQ → GOAL → AC → QS 顺序（事件序列即证据）。"""
        req = _make_req(mock_pid, tmp_project_root)
        sut.assemble_four_set(req, project_root=str(tmp_project_root))
        events = [c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list]
        # 期望序列（至少含 4 步 ready 事件）
        expected_order = ["requirements_ready", "goals_ready", "ac_ready", "quality_ready"]
        # 在 events 中保持相对顺序
        indices = [events.index(e) for e in expected_order if e in events]
        assert indices == sorted(indices), f"events out of order: {events}"
        assert len(set(expected_order) - set(events)) == 0, "missing ready events"

    def test_TC_L102_L203_004_4_pieces_ready_event(
        self, sut: FourPiecesProducer, mock_pid: str, tmp_project_root: Path,
        mock_event_bus: MagicMock,
    ) -> None:
        """总事件 4_pieces_ready 带 manifest_hash + 4 path。"""
        req = _make_req(mock_pid, tmp_project_root)
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        calls = mock_event_bus.append_event.call_args_list
        total_events = [c for c in calls if c.kwargs["event_type"] == "4_pieces_ready"]
        assert len(total_events) == 1
        payload = total_events[0].kwargs["payload"]
        assert "manifest_hash" in payload
        assert "paths" in payload
        assert len(payload["paths"]) == 4


class TestL2_03_FourSet_ErrorCodes:
    """错误码分支。"""

    def test_TC_L102_L203_106_pm14_pid_mismatch(
        self, sut: FourPiecesProducer, mock_pid: str, tmp_project_root: Path,
    ) -> None:
        """req.project_id != context.project_id（跨项目误入）· E_PM14_PID_MISMATCH。"""
        wrong_pid = "p_99999999-9999-9999-9999-999999999999"
        _setup_upstream(tmp_project_root, mock_pid)  # 真 pid 的 upstream
        req = FourSetRequest(
            project_id=wrong_pid,  # mismatch
            request_id="r1",
            stage="S2",
            context=FourSetContext(
                charter_path=str(tmp_project_root / "projects" / mock_pid / "chart" / "HarnessFlowGoal.md"),
                stakeholders_path=str(tmp_project_root / "projects" / mock_pid / "chart" / "HarnessFlowPrdScope.md"),
                goal_anchor_hash="sha256:" + "a" * 64,
            ),
            caller_l2="L2-01",
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert isinstance(resp.result, StructuredErr)
        assert resp.result.err_type == E_PM14_PID_MISMATCH

    def test_TC_L102_L203_101_upstream_missing(
        self, sut: FourPiecesProducer, mock_pid: str, tmp_project_root: Path,
    ) -> None:
        """charter_path 不存在 · E_UPSTREAM_MISSING。"""
        req = FourSetRequest(
            project_id=mock_pid,
            request_id="r1",
            stage="S2",
            context=FourSetContext(
                charter_path="/nonexistent/path/HarnessFlowGoal.md",
                stakeholders_path="/nonexistent/path/HarnessFlowPrdScope.md",
                goal_anchor_hash="sha256:" + "a" * 64,
            ),
            caller_l2="L2-01",
        )
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert isinstance(resp.result, StructuredErr)
        assert resp.result.err_type == E_UPSTREAM_MISSING

    def test_TC_L102_L203_103_traceability_broken(
        self, mock_pid: str, tmp_project_root: Path,
        mock_template: MagicMock, mock_event_bus: MagicMock,
    ) -> None:
        """skill 返回 AC 引用不存在的 GOAL-99 · E_TRACEABILITY_BROKEN。"""
        bad_skill = MagicMock()

        def _bad_delegate(*, role, **kwargs):
            if role == "requirements-analysis":
                return {"items": [{"id": "REQ-001", "description": "x", "priority": "P0"}]}
            if role == "goals-writing":
                return {"items": [{"id": "GOAL-001", "statement": "x", "linked_reqs": ["REQ-001"]}]}
            if role == "ac-scenario-writer":
                return {"items": [{
                    "id": "AC-001", "given": "g", "when": "w", "then": "t",
                    "linked_goal": "GOAL-99",  # 不存在
                }]}
            if role == "quality-audit":
                return {"items": [{
                    "id": "QS-001", "measurable_criteria": "x",
                    "verification_method": "e2e_test", "linked_ac": "AC-001",
                }]}
            return {"items": []}

        bad_skill.delegate_subagent.side_effect = _bad_delegate
        sut = FourPiecesProducer(
            template=mock_template, skill=bad_skill, event_bus=mock_event_bus,
        )
        req = _make_req(mock_pid, tmp_project_root)
        resp = sut.assemble_four_set(req, project_root=str(tmp_project_root))
        assert resp.status == "err"
        assert isinstance(resp.result, StructuredErr)
        assert resp.result.err_type == E_TRACEABILITY_BROKEN
