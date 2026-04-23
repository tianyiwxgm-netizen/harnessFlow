"""L2-02 StartupProducer public API 测试 · 对齐 3-2 TDD md §2 TC-001/002/003/020。

StartupProducer 是 L2-01 调用的入口 · 包装 produce_kickoff + validate_trigger。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.kickoff.producer import StartupProducer
from app.project_lifecycle.kickoff.schemas import (
    KickoffErr,
    KickoffRequest,
    KickoffResponse,
    KickoffSuccess,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def mock_brainstorm() -> MagicMock:
    m = MagicMock()
    m.invoke.return_value = {
        "rounds": 2, "is_confirmed": True,
        "slots": {"goals": ["ship"], "in_scope": ["auth"]},
    }
    return m


@pytest.fixture
def mock_template_engine() -> MagicMock:
    m = MagicMock()
    m.render_template.side_effect = [
        MagicMock(output="---\ntemplate_id: kickoff.goal.v1.0\n---\n# G\nbody"),
        MagicMock(output="---\ntemplate_id: kickoff.scope.v1.0\n---\n# S\nbody"),
    ]
    return m


@pytest.fixture
def mock_event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(tmp_project_root, mock_brainstorm, mock_template_engine, mock_event_bus) -> StartupProducer:
    return StartupProducer(
        brainstorm=mock_brainstorm,
        template=mock_template_engine,
        event_bus=mock_event_bus,
        project_root=str(tmp_project_root),
    )


def _make_req(**overrides) -> KickoffRequest:
    base = dict(
        trigger_id="trig-001",
        stage="S1",
        user_initial_goal="做一个 todo 应用",
        caller_l2="L2-01",
        trim_level="full",
    )
    base.update(overrides)
    return KickoffRequest(**base)


class TestL2_02_StartupProducer:

    def test_TC_L102_L202_001_kickoff_full_trim_success(
        self, sut: StartupProducer,
    ) -> None:
        """full trim · 2 轮澄清 · 返 ok + KickoffSuccess。"""
        req = _make_req(trim_level="full")
        resp: KickoffResponse = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert resp.trigger_id == "trig-001"
        assert isinstance(resp.result, KickoffSuccess)
        assert resp.result.project_id.startswith("p_")
        assert resp.result.charter_path.endswith("HarnessFlowGoal.md")
        assert resp.result.stakeholders_path.endswith("HarnessFlowPrdScope.md")
        assert resp.result.goal_anchor_hash.startswith("sha256:")
        assert resp.result.clarification_rounds == 2
        assert resp.result.clarification_incomplete is False
        assert resp.result.events_published == (
            "project_created", "charter_ready",
            "stakeholders_ready", "goal_anchor_hash_locked",
        )
        assert resp.result.trim_level_applied == "full"
        assert resp.latency_ms >= 0

    def test_TC_L102_L202_002_kickoff_minimal_trim_success(
        self, sut: StartupProducer,
    ) -> None:
        """minimal trim · 返 ok · trim_level_applied=minimal。"""
        req = _make_req(trim_level="minimal", user_initial_goal="API 原型")
        resp = sut.kickoff_create_project(req)
        assert resp.status == "ok"
        assert isinstance(resp.result, KickoffSuccess)
        assert resp.result.trim_level_applied == "minimal"

    def test_TC_L102_L202_020_validate_trigger_stage_s1_only(
        self, sut: StartupProducer,
    ) -> None:
        """stage != S1 立即拒 · 返 status=err · 不触发下游。"""
        req = _make_req(stage="S2")
        resp = sut.kickoff_create_project(req)
        assert resp.status == "err"
        assert isinstance(resp.result, KickoffErr)
        assert "stage" in resp.result.reason.lower()

    def test_TC_L102_L202_020b_validate_caller_l2_must_be_L2_01(
        self, sut: StartupProducer,
    ) -> None:
        """caller_l2 必为 L2-01 · 其他拒。"""
        req = _make_req(caller_l2="L2-03")
        resp = sut.kickoff_create_project(req)
        assert resp.status == "err"
        assert isinstance(resp.result, KickoffErr)

    def test_TC_L102_L202_020c_empty_user_goal_rejected(
        self, sut: StartupProducer,
    ) -> None:
        """user_initial_goal 空字符串 · 拒。"""
        req = _make_req(user_initial_goal="")
        resp = sut.kickoff_create_project(req)
        assert resp.status == "err"
        assert isinstance(resp.result, KickoffErr)

    def test_TC_L102_L202_brainstorm_failure_returns_err_response(
        self, tmp_project_root: Path, mock_template_engine, mock_event_bus,
    ) -> None:
        """brainstorm 崩 · KickoffError 被 StartupProducer 捕获 · 返 status=err · 不抛。"""
        failing_brainstorm = MagicMock()
        failing_brainstorm.invoke.side_effect = RuntimeError("OOM")
        sut_fail = StartupProducer(
            brainstorm=failing_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        req = _make_req()
        resp = sut_fail.kickoff_create_project(req)
        assert resp.status == "err"
        assert isinstance(resp.result, KickoffErr)
        assert resp.result.err_code == "E_L102_L202_015"

    def test_TC_L102_L202_latency_ms_populated(
        self, sut: StartupProducer,
    ) -> None:
        """latency_ms 字段非零（整数毫秒）。"""
        req = _make_req()
        resp = sut.kickoff_create_project(req)
        assert resp.latency_ms >= 0
