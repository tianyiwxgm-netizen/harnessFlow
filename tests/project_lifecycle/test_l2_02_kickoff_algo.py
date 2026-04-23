"""L2-02 内部算法单元测试 · atomic_write_chart + compute_anchor_hash。

对齐 3-2 TDD md §2 TC-011~015。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.project_lifecycle.kickoff.algo import (
    atomic_write_chart,
    compute_anchor_hash,
)
from app.project_lifecycle.kickoff.errors import (
    E_ATOMIC_WRITE_FAILED,
    E_CROSS_PROJECT_PATH,
    E_POST_WRITE_HASH_MISMATCH,
    KickoffError,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """projects/ 根目录 fixture · PM-14 分片测试用。"""
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


class TestL2_02_AtomicWriteChart:
    """§6.3 algo · atomic_write_chart 原子写 + sha256 复核。"""

    def test_TC_L102_L202_011_atomic_write_tempfile_then_rename(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """写后路径存在且无 .tmp 残留。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        atomic_write_chart(str(path), "# hello")
        assert path.exists()
        assert not any(p.name.endswith(".tmp") for p in path.parent.iterdir())

    def test_TC_L102_L202_012_atomic_write_post_hash_matches(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """写后读回 sha256 与 sha256(content) 一致。"""
        path = tmp_project_root / f"projects/{mock_project_id}/chart/HarnessFlowGoal.md"
        content = "# hello\n内容"
        atomic_write_chart(str(path), content)
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert expected == actual

    def test_TC_L102_L202_112_cross_project_path_rejected(
        self, tmp_project_root: Path,
    ) -> None:
        """路径前缀非 projects/<pid>/ · E_L102_L202_012 拒写。"""
        bad = tmp_project_root / "elsewhere/HarnessFlowGoal.md"
        with pytest.raises(KickoffError) as exc:
            atomic_write_chart(str(bad), "# x")
        assert exc.value.error_code == E_CROSS_PROJECT_PATH


class TestL2_02_ComputeAnchorHash:
    """§6.4 algo · compute_anchor_hash 幂等 + 忽略 frontmatter 可变字段。"""

    def test_TC_L102_L202_013_compute_anchor_hash_basic(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """goal + scope 拼接 sha256 · 返 64 hex。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# G\ngoal body", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\nscope body", encoding="utf-8")
        h = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        assert isinstance(h, str)
        assert len(h) == 64

    def test_TC_L102_L202_014_anchor_hash_excludes_frontmatter(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """正文一致但 frontmatter updated_at 变 · hash 不变。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        body = "# G\ngoal body"
        (root / "HarnessFlowGoal.md").write_text(
            f"---\nupdated_at: 2026-01-01\n---\n{body}", encoding="utf-8",
        )
        (root / "HarnessFlowPrdScope.md").write_text("# S\nscope body", encoding="utf-8")
        h1 = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        # 改 frontmatter updated_at
        (root / "HarnessFlowGoal.md").write_text(
            f"---\nupdated_at: 2026-04-22\n---\n{body}", encoding="utf-8",
        )
        h2 = compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
        assert h1 == h2

    def test_TC_L102_L202_015_anchor_hash_idempotent(
        self, mock_project_id: str, tmp_project_root: Path,
    ) -> None:
        """同内容 10 次 compute · hash 集合大小 1。"""
        root = tmp_project_root / f"projects/{mock_project_id}/chart"
        root.mkdir(parents=True, exist_ok=True)
        (root / "HarnessFlowGoal.md").write_text("# G\nbody", encoding="utf-8")
        (root / "HarnessFlowPrdScope.md").write_text("# S\nbody", encoding="utf-8")
        hashes = {
            compute_anchor_hash(mock_project_id, root_dir=str(tmp_project_root))
            for _ in range(10)
        }
        assert len(hashes) == 1
