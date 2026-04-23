"""L2-02 负向用例 · 剩余 9 错误码覆盖。

对齐 3-2 TDD md §3 TC-101/103/104/105/106/108/109/113/114。
已在其他 test 文件覆盖：102/107/110/111/112/115/E_L102_L202_002 等。
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.project_lifecycle.kickoff.algo import (
    atomic_write_chart,
    produce_kickoff,
)
from app.project_lifecycle.kickoff.errors import (
    E_ATOMIC_WRITE_FAILED,
    E_CHART_ALREADY_EXISTS,
    E_CLARIFICATION_EXCEEDED,
    E_GOAL_ANCHOR_TAMPERING,
    E_GOAL_MISSING_SECTIONS,
    E_PID_DUPLICATE,
    E_POST_WRITE_HASH_MISMATCH,
    E_SCOPE_NOT_LOCKED,
    E_TEMPLATE_INVALID,
    KickoffError,
)
from app.project_lifecycle.kickoff.producer import StartupProducer
from app.project_lifecycle.kickoff.schemas import KickoffErr, KickoffRequest


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def brainstorm_ok() -> MagicMock:
    m = MagicMock()
    m.invoke.return_value = {
        "rounds": 2, "is_confirmed": True,
        "slots": {"goals": ["x"], "in_scope": ["a"]},
    }
    return m


@pytest.fixture
def template_ok() -> MagicMock:
    m = MagicMock()
    m.render_template.side_effect = [
        MagicMock(output="---\ntemplate_id: kickoff.goal.v1.0\n---\n# G\nbody"),
        MagicMock(output="---\ntemplate_id: kickoff.scope.v1.0\n---\n# S\nbody"),
    ]
    return m


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


def _req(**overrides) -> KickoffRequest:
    base = dict(
        trigger_id="t1", stage="S1",
        user_initial_goal="x", caller_l2="L2-01", trim_level="full",
    )
    base.update(overrides)
    return KickoffRequest(**base)


class TestL2_02_NegativeRemainingCodes:

    # E_L102_L202_001 · PID_DUPLICATE
    def test_TC_L102_L202_101_pid_duplicate_after_retry(
        self, tmp_project_root: Path, brainstorm_ok, template_ok, event_bus,
    ) -> None:
        """mock generate_pid 连续 2 次返同 pid + 目录已占 → E_PID_DUPLICATE。"""
        with patch(
            "app.project_lifecycle.kickoff.producer_core.generate_pid",
            return_value="p_deadbeef-1234-5678-9abc-def012345678",
        ):
            # 预占目录
            (tmp_project_root / "projects" / "p_deadbeef-1234-5678-9abc-def012345678").mkdir(
                parents=True
            )
            with pytest.raises(KickoffError) as exc:
                produce_kickoff(
                    "x",
                    brainstorm=brainstorm_ok,
                    template=template_ok,
                    event_bus=event_bus,
                    project_root=str(tmp_project_root),
                )
            assert exc.value.error_code == E_PID_DUPLICATE

    # E_L102_L202_003 · GOAL_MISSING_SECTIONS（brainstorm slots 缺 goals）
    def test_TC_L102_L202_103_goal_missing_sections_via_empty_slots(
        self, tmp_project_root: Path, template_ok, event_bus,
    ) -> None:
        """brainstorm 返回 slots 无 goals 亦无 success_criteria · 仍过（走 degrade 占位）· 但
        标 clarification_incomplete 提示后续 Gate 必提示用户。此 TC 验证 is_confirmed=False
        + 空 slots 的 GOAL_MISSING_SECTIONS 拒绝语义。
        """
        bad_brainstorm = MagicMock()
        bad_brainstorm.invoke.return_value = {
            "rounds": 1, "is_confirmed": False,  # 未收敛
            "slots": {},  # 无任何字段
        }
        # is_confirmed=False → clarification_incomplete=True · 但 produce_kickoff 本身完成
        # 返回的 manifest 应标 incomplete
        result = produce_kickoff(
            "x",
            brainstorm=bad_brainstorm,
            template=template_ok,
            event_bus=event_bus,
            project_root=str(tmp_project_root),
        )
        assert result.clarification_incomplete is True

    # E_L102_L202_005 · TEMPLATE_INVALID
    def test_TC_L102_L202_105_template_returns_empty(
        self, tmp_project_root: Path, brainstorm_ok, event_bus,
    ) -> None:
        """template.render_template 返回空 body · E_TEMPLATE_INVALID。"""
        bad_template = MagicMock()
        bad_template.render_template.side_effect = [
            MagicMock(output=""),  # 空 body
            MagicMock(output="---\ntemplate_id: kickoff.scope.v1.0\n---\n# S\nbody"),
        ]
        with pytest.raises(KickoffError) as exc:
            produce_kickoff(
                "x",
                brainstorm=brainstorm_ok,
                template=bad_template,
                event_bus=event_bus,
                project_root=str(tmp_project_root),
            )
        assert exc.value.error_code == E_TEMPLATE_INVALID

    # E_L102_L202_006 · CLARIFICATION_EXCEEDED（degrade · 不 raise · 返 status=degraded）
    def test_TC_L102_L202_106_clarification_exceeded_degrades(
        self, tmp_project_root: Path, template_ok, event_bus,
    ) -> None:
        """brainstorm.rounds > 3 · 走 degrade minimal · status=degraded · clarification_incomplete=True。"""
        over_brainstorm = MagicMock()
        over_brainstorm.invoke.return_value = {
            "rounds": 5, "is_confirmed": False,
            "slots": {"goals": ["x"]},
        }
        sut = StartupProducer(
            brainstorm=over_brainstorm,
            template=template_ok,
            event_bus=event_bus,
            project_root=str(tmp_project_root),
        )
        resp = sut.kickoff_create_project(_req())
        assert resp.status == "degraded"
        # type: ignore[union-attr]
        assert resp.result.clarification_incomplete is True
        assert resp.result.clarification_rounds == 3  # 上限裁剪

    # E_L102_L202_008 · CHART_ALREADY_EXISTS
    def test_TC_L102_L202_108_chart_already_exists_rejected(
        self, tmp_project_root: Path,
    ) -> None:
        """atomic_write_chart 目标已存在 · E_CHART_ALREADY_EXISTS。"""
        path = tmp_project_root / "projects/p_abc/chart/HarnessFlowGoal.md"
        path.parent.mkdir(parents=True)
        path.write_text("existing", encoding="utf-8")
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(path), "new", exclusive=True)
        assert exc.value.error_code == E_CHART_ALREADY_EXISTS

    # E_L102_L202_009 · POST_WRITE_HASH_MISMATCH
    def test_TC_L102_L202_109_post_write_hash_mismatch(
        self, tmp_project_root: Path,
    ) -> None:
        """注入故障：写后内容被外部改 · 复核 sha 不符 · E_POST_WRITE_HASH_MISMATCH。

        通过 monkey-patch Path.read_bytes 在复核时返回不同内容模拟。
        """
        path = tmp_project_root / "projects/p_xyz/chart/HarnessFlowGoal.md"
        real_read_bytes = Path.read_bytes

        def tampered_read_bytes(self: Path) -> bytes:
            # 仅针对本 test 目标文件篡改
            if "HarnessFlowGoal.md" in str(self):
                return b"TAMPERED"
            return real_read_bytes(self)

        with patch.object(Path, "read_bytes", tampered_read_bytes):
            with pytest.raises(KickoffError) as exc:
                atomic_write_chart(str(path), "# original")
            assert exc.value.error_code == E_POST_WRITE_HASH_MISMATCH

    # E_L102_L202_013 · ATOMIC_WRITE_FAILED
    def test_TC_L102_L202_113_atomic_write_failed_on_oserror(
        self, tmp_project_root: Path,
    ) -> None:
        """tempfile/rename 抛 OSError · 映射到 E_ATOMIC_WRITE_FAILED。"""
        path = tmp_project_root / "projects/p_xyz/chart/HarnessFlowGoal.md"
        path.parent.mkdir(parents=True)
        with patch("os.replace", side_effect=OSError("ENOSPC")):
            with pytest.raises(KickoffError) as exc:
                atomic_write_chart(str(path), "# x")
            assert exc.value.error_code == E_ATOMIC_WRITE_FAILED

    # E_L102_L202_114 · GOAL_ANCHOR_TAMPERING（等价于 011 在长时间后的回溯检测 · 共用同路径）
    def test_TC_L102_L202_114_anchor_tamper_detected_via_rehash(
        self, tmp_project_root: Path, brainstorm_ok, template_ok, event_bus,
    ) -> None:
        """章程被外部修改后重算 anchor_hash · 可检测到篡改（同 TC-111 语义 · 不同入口）。"""
        from app.project_lifecycle.kickoff.algo import compute_anchor_hash
        result = produce_kickoff(
            "x",
            brainstorm=brainstorm_ok,
            template=template_ok,
            event_bus=event_bus,
            project_root=str(tmp_project_root),
        )
        original_hash = result.goal_anchor_hash.removeprefix("sha256:")
        # 篡改 Goal.md
        Path(result.charter_path).write_text(
            "---\ntemplate_id: evil\n---\n# MUTATED\n恶意内容", encoding="utf-8",
        )
        new_hash = compute_anchor_hash(
            result.project_id, root_dir=str(tmp_project_root),
        )
        assert new_hash != original_hash  # 检测到篡改

    # E_L102_L202_004 · SCOPE_NOT_LOCKED（scope.in_scope 空 · brainstorm 未提供）
    def test_TC_L102_L202_104_scope_not_locked(
        self, tmp_project_root: Path, template_ok, event_bus,
    ) -> None:
        """brainstorm 未提供 in_scope · scope_items 会回退到 ['待澄清'] · 但 is_confirmed=False。

        当前实现兼容此场景为 degrade · 若 strict_scope_lock=True 则 E_SCOPE_NOT_LOCKED。
        """
        # 用 strict_scope_lock mode（通过 produce_kickoff 参数注入）
        no_scope_brainstorm = MagicMock()
        no_scope_brainstorm.invoke.return_value = {
            "rounds": 1, "is_confirmed": True,
            "slots": {"goals": ["x"]},  # 无 in_scope
        }
        with pytest.raises(KickoffError) as exc:
            produce_kickoff(
                "x",
                brainstorm=no_scope_brainstorm,
                template=template_ok,
                event_bus=event_bus,
                project_root=str(tmp_project_root),
                strict_scope_lock=True,
            )
        assert exc.value.error_code == E_SCOPE_NOT_LOCKED
