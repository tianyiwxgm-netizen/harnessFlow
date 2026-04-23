"""L2-02 activate_project_id + recover_draft 测试。

对齐 3-2 TDD md §2 TC-009/010/016/017/018 + §3 TC-102/107/110/111。

PM-14 硬约束重点：
  - activate_project_id 调用方必是 L2-01 · 其他 L2 拒绝（E_PM14_OWNERSHIP_VIOLATION）
  - anchor_hash 篡改检测（激活前复核 · E_ANCHOR_HASH_MISMATCH）
  - user_confirmed=False 拒绝（E_USER_NOT_CONFIRMED）
  - 非 DRAFT 状态拒激活（E_STATE_NOT_DRAFT）
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from app.project_lifecycle.kickoff.activator import activate_project_id
from app.project_lifecycle.kickoff.algo import produce_kickoff
from app.project_lifecycle.kickoff.errors import (
    E_ANCHOR_HASH_MISMATCH,
    E_PM14_OWNERSHIP_VIOLATION,
    E_STATE_NOT_DRAFT,
    E_USER_NOT_CONFIRMED,
    KickoffError,
)
from app.project_lifecycle.kickoff.recovery import recover_draft
from app.project_lifecycle.kickoff.schemas import (
    ActivateRequest,
    ActivateResponse,
    RecoveryResult,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def fresh_draft_project(
    tmp_project_root: Path,
) -> tuple[str, Path]:
    """跑一次 produce_kickoff 产生一个 DRAFT project · 返 (pid, root)。"""
    brainstorm = MagicMock()
    brainstorm.invoke.return_value = {
        "rounds": 1, "is_confirmed": True, "slots": {"goals": ["x"]},
    }
    template = MagicMock()
    template.render_template.side_effect = [
        MagicMock(output="---\ntemplate_id: kickoff.goal.v1.0\n---\n# G\nbody g"),
        MagicMock(output="---\ntemplate_id: kickoff.scope.v1.0\n---\n# S\nbody s"),
    ]
    event_bus = MagicMock()
    result = produce_kickoff(
        "user utterance",
        brainstorm=brainstorm,
        template=template,
        event_bus=event_bus,
        project_root=str(tmp_project_root),
    )
    return result.project_id, tmp_project_root


class TestL2_02_ActivateProjectId:
    """activate_project_id · PM-14 硬约束 + state 转换 DRAFT → INITIALIZED。"""

    def test_TC_L102_L202_009_activate_draft_to_initialized(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        req = ActivateRequest(
            project_id=pid,
            goal_anchor_hash=manifest["goal_anchor_hash"],
            user_confirmed=True,
            charter_path=manifest["charter_path"],
            stakeholders_path=manifest["stakeholders_path"],
            caller_l2="L2-01",
        )
        resp: ActivateResponse = activate_project_id(req, project_root=str(root))
        assert resp.state == "INITIALIZED"
        assert resp.project_id == pid
        assert resp.meta_path.endswith("created.json")
        # state.json 更新
        state = json.loads(
            (root / "projects" / pid / "meta" / "state.json").read_text(encoding="utf-8")
        )
        assert state["state"] == "INITIALIZED"
        # created.json 写入
        created_path = root / "projects" / pid / "meta" / "created.json"
        assert created_path.exists()

    def test_TC_L102_L202_010_activate_rechecks_anchor_hash(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        """activate 时读取章程重算 anchor_hash · 与入参一致才允许。"""
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        req = ActivateRequest(
            project_id=pid,
            goal_anchor_hash=manifest["goal_anchor_hash"],
            user_confirmed=True,
            charter_path=manifest["charter_path"],
            stakeholders_path=manifest["stakeholders_path"],
            caller_l2="L2-01",
        )
        resp = activate_project_id(req, project_root=str(root))
        assert resp.state == "INITIALIZED"

    def test_TC_L102_L202_102_activate_without_user_confirm_rejected(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        req = ActivateRequest(
            project_id=pid,
            goal_anchor_hash=manifest["goal_anchor_hash"],
            user_confirmed=False,
            charter_path=manifest["charter_path"],
            stakeholders_path=manifest["stakeholders_path"],
            caller_l2="L2-01",
        )
        with pytest.raises(KickoffError) as exc:
            activate_project_id(req, project_root=str(root))
        assert exc.value.error_code == E_USER_NOT_CONFIRMED

    def test_TC_L102_L202_110_non_L2_01_caller_rejected(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        """PM-14 越权 · 非 L2-01 调用方 · E_PM14_OWNERSHIP_VIOLATION。"""
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        for bad_caller in ("L2-02", "L2-03", "L1-05", "external", ""):
            req = ActivateRequest(
                project_id=pid,
                goal_anchor_hash=manifest["goal_anchor_hash"],
                user_confirmed=True,
                charter_path=manifest["charter_path"],
                stakeholders_path=manifest["stakeholders_path"],
                caller_l2=bad_caller,
            )
            with pytest.raises(KickoffError) as exc:
                activate_project_id(req, project_root=str(root))
            assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION, f"caller={bad_caller!r}"

    def test_TC_L102_L202_111_anchor_hash_tampered_rejected(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        """章程被外部修改 · activate 时重算 anchor_hash 不符 · E_ANCHOR_HASH_MISMATCH。"""
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        # 篡改章程内容
        goal_path = Path(manifest["charter_path"])
        goal_path.write_text("---\ntemplate_id: x\n---\n# TAMPERED\n恶意改动", encoding="utf-8")

        req = ActivateRequest(
            project_id=pid,
            goal_anchor_hash=manifest["goal_anchor_hash"],  # 原 hash
            user_confirmed=True,
            charter_path=manifest["charter_path"],
            stakeholders_path=manifest["stakeholders_path"],
            caller_l2="L2-01",
        )
        with pytest.raises(KickoffError) as exc:
            activate_project_id(req, project_root=str(root))
        assert exc.value.error_code == E_ANCHOR_HASH_MISMATCH

    def test_TC_L102_L202_107_state_not_draft_rejected(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        """state 非 DRAFT · E_STATE_NOT_DRAFT。第一次 activate 成功，第二次应拒。"""
        pid, root = fresh_draft_project
        manifest = yaml.safe_load(
            (root / "projects" / pid / "meta" / "project_manifest.yaml").read_text(encoding="utf-8")
        )
        req = ActivateRequest(
            project_id=pid,
            goal_anchor_hash=manifest["goal_anchor_hash"],
            user_confirmed=True,
            charter_path=manifest["charter_path"],
            stakeholders_path=manifest["stakeholders_path"],
            caller_l2="L2-01",
        )
        # 首次成功
        activate_project_id(req, project_root=str(root))
        # 二次 reject · state 已 INITIALIZED
        with pytest.raises(KickoffError) as exc:
            activate_project_id(req, project_root=str(root))
        assert exc.value.error_code == E_STATE_NOT_DRAFT


class TestL2_02_RecoverDraft:
    """recover_draft · 崩溃恢复（全齐续传 / 半成品清理 / no_op）· 对齐 §6.5。"""

    def test_TC_L102_L202_018_recover_draft_no_op_when_not_started(
        self, tmp_project_root: Path,
    ) -> None:
        pid = "p_nonexistent"
        event_bus = MagicMock()
        result: RecoveryResult = recover_draft(
            pid, root_dir=str(tmp_project_root), event_bus=event_bus,
        )
        assert result.action == "no_op"
        event_bus.append_event.assert_not_called()

    def test_TC_L102_L202_016_recover_draft_resume_when_full(
        self, fresh_draft_project: tuple[str, Path],
    ) -> None:
        """全齐（goal + scope + manifest + state.json DRAFT）· resume · 重放 s1_ready。"""
        pid, root = fresh_draft_project
        event_bus = MagicMock()
        result = recover_draft(pid, root_dir=str(root), event_bus=event_bus)
        assert result.action == "resumed"
        event_bus.append_event.assert_called_with(
            project_id=pid,
            event_type="s1_ready",
            payload={"recovered": True},
        )

    def test_TC_L102_L202_017_recover_draft_cleans_partial(
        self, tmp_project_root: Path,
    ) -> None:
        """半成品（只 goal 无 scope）· 清 rmtree · 发 kickoff_rolled_back。"""
        pid = "p_partial1234-5678-90ab-cdef-1234567890ab"
        root = tmp_project_root / "projects" / pid
        (root / "chart").mkdir(parents=True, exist_ok=True)
        (root / "meta").mkdir(parents=True, exist_ok=True)
        (root / "meta" / "state.json").write_text(
            '{"state": "DRAFT", "project_id": "' + pid + '"}', encoding="utf-8",
        )
        (root / "chart" / "HarnessFlowGoal.md").write_text("# g", encoding="utf-8")
        # 故意无 scope / 无 manifest
        event_bus = MagicMock()
        result = recover_draft(pid, root_dir=str(tmp_project_root), event_bus=event_bus)
        assert result.action == "rolled_back"
        assert not root.exists()
        event_bus.append_event.assert_called_with(
            project_id=pid,
            event_type="kickoff_rolled_back",
            payload={"reason": "partial_draft_found"},
        )
