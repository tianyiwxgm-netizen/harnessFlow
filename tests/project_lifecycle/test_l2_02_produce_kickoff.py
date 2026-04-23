"""L2-02 produce_kickoff 主循环测试 · 对齐 3-2 TDD md §2 TC-004/005/019/020 + PID gen。

TDD · RED 阶段：期望 `app.project_lifecycle.kickoff.algo.produce_kickoff` 存在。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.kickoff.algo import (
    generate_pid,
    is_valid_pid,
    produce_kickoff,
)
from app.project_lifecycle.kickoff.errors import (
    E_BRAINSTORM_SUBAGENT_FAILED,
    KickoffError,
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
        "rounds": 2,
        "is_confirmed": True,
        "slots": {
            "goals": ["上线 MVP", "支持 markdown"],
            "in_scope": ["认证", "文章 CRUD"],
            "out_of_scope": ["支付"],
            "constraints": ["2 周内"],
            "deadline": "2026-06-30",
        },
    }
    return m


@pytest.fixture
def mock_template_engine() -> MagicMock:
    m = MagicMock()
    # render_template 两次调用 · 分别返回 goal / scope 模板 rendered body
    m.render_template.side_effect = [
        MagicMock(output="---\ntemplate_id: kickoff.goal.v1.0\n---\n# Goal\nbody goal"),
        MagicMock(output="---\ntemplate_id: kickoff.scope.v1.0\n---\n# Scope\nbody scope"),
    ]
    return m


@pytest.fixture
def mock_event_bus() -> MagicMock:
    m = MagicMock()
    return m


class TestL2_02_PidGen:

    def test_TC_L102_L202_000a_generate_pid_format(self) -> None:
        pid = generate_pid()
        assert pid.startswith("p_")
        assert is_valid_pid(pid)

    def test_TC_L102_L202_000b_is_valid_pid_rejects_ulid_format(self) -> None:
        assert not is_valid_pid("01HXKABCDEFG12345678MNPQRS")
        assert not is_valid_pid("")
        assert not is_valid_pid(None)  # type: ignore[arg-type]
        assert not is_valid_pid("p_invalid")


class TestL2_02_ProduceKickoff:

    def test_TC_L102_L202_004_produce_kickoff_main_loop_full_path(
        self, tmp_project_root: Path,
        mock_brainstorm: MagicMock,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """§6.1 主循环 8 步全路径 · 产 pid + 2 章程 + manifest + 4 事件。"""
        result = produce_kickoff(
            "做一个 todo 应用",
            brainstorm=mock_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        # pid 合法
        assert is_valid_pid(result.project_id)
        # 2 章程 + manifest 落盘
        assert Path(result.charter_path).exists()
        assert Path(result.stakeholders_path).exists()
        assert Path(result.manifest_path).exists()
        assert result.charter_path.endswith("HarnessFlowGoal.md")
        assert result.stakeholders_path.endswith("HarnessFlowPrdScope.md")
        # anchor_hash 格式
        assert result.goal_anchor_hash.startswith("sha256:")
        assert len(result.goal_anchor_hash) == len("sha256:") + 64
        # 澄清轮数
        assert result.clarification_rounds == 2
        assert result.clarification_incomplete is False

    def test_TC_L102_L202_019_publish_4_events_in_order(
        self, tmp_project_root: Path,
        mock_brainstorm: MagicMock,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """4 事件按顺序 emit · project_created → charter_ready → stakeholders_ready → goal_anchor_hash_locked。"""
        produce_kickoff(
            "x",
            brainstorm=mock_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        emitted = [c.kwargs["event_type"] for c in mock_event_bus.append_event.call_args_list]
        assert emitted[:4] == [
            "project_created",
            "charter_ready",
            "stakeholders_ready",
            "goal_anchor_hash_locked",
        ]
        assert tuple(emitted[:4]) == tuple(["project_created", "charter_ready", "stakeholders_ready", "goal_anchor_hash_locked"])

    def test_TC_L102_L202_005_produce_kickoff_writes_state_json_draft(
        self, tmp_project_root: Path,
        mock_brainstorm: MagicMock,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """projects/<pid>/meta/state.json 内容为 DRAFT · recover_draft 读它判定。"""
        import json
        result = produce_kickoff(
            "x",
            brainstorm=mock_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        state_path = tmp_project_root / "projects" / result.project_id / "meta" / "state.json"
        assert state_path.exists()
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert state_data["state"] == "DRAFT"
        assert state_data["project_id"] == result.project_id

    def test_TC_L102_L207_create_directory_tree(
        self, tmp_project_root: Path,
        mock_brainstorm: MagicMock,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """建目录 · chart / meta / stage-gates 子目录齐。"""
        result = produce_kickoff(
            "x",
            brainstorm=mock_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        base = tmp_project_root / "projects" / result.project_id
        assert (base / "chart").is_dir()
        assert (base / "meta").is_dir()
        assert (base / "stage-gates").is_dir()

    def test_TC_L102_L202_115_brainstorm_subagent_fails(
        self, tmp_project_root: Path,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """brainstorm subagent 崩溃 · E_BRAINSTORM_SUBAGENT_FAILED。"""
        failing_brainstorm = MagicMock()
        failing_brainstorm.invoke.side_effect = RuntimeError("subagent OOM")
        with pytest.raises(KickoffError) as exc:
            produce_kickoff(
                "x",
                brainstorm=failing_brainstorm,
                template=mock_template_engine,
                event_bus=mock_event_bus,
                project_root=str(tmp_project_root),
            )
        assert exc.value.error_code == E_BRAINSTORM_SUBAGENT_FAILED

    def test_TC_L102_L202_anchor_hash_matches_manifest_yaml(
        self, tmp_project_root: Path,
        mock_brainstorm: MagicMock,
        mock_template_engine: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """manifest.yaml 中记录的 goal_anchor_hash 与返回的 goal_anchor_hash 一致。"""
        import yaml
        result = produce_kickoff(
            "x",
            brainstorm=mock_brainstorm,
            template=mock_template_engine,
            event_bus=mock_event_bus,
            project_root=str(tmp_project_root),
        )
        manifest = yaml.safe_load(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["goal_anchor_hash"] == result.goal_anchor_hash
        assert manifest["state"] == "DRAFT"
        assert manifest["project_id"] == result.project_id
