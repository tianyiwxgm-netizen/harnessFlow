"""L2-06 Closing + Archive 测试（核心 TC）。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.project_lifecycle.closing import (
    ArchiveManifest,
    ClosingError,
    ClosingExecutor,
    ClosingResult,
    PurgeResult,
)
from app.project_lifecycle.closing.errors import (
    E_PM14_OWNERSHIP_VIOLATION,
    E_PURGE_TOKEN_MISMATCH,
    E_PURGE_TOO_EARLY,
    E_STATE_NOT_CLOSING_APPROVED,
    E_UPSTREAM_NOT_READY,
)


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def pid() -> str:
    return "p_closing0-1234-5678-9abc-def012345678"


@pytest.fixture
def template_ok() -> MagicMock:
    m = MagicMock()
    m.render_template = lambda **kw: MagicMock(
        output=f"---\ntemplate_id: {kw['kind']}.v1.0\n---\n# {kw['kind']}\nbody"
    )
    return m


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(template_ok, event_bus) -> ClosingExecutor:
    return ClosingExecutor(template=template_ok, event_bus=event_bus)


def _setup_draft_project(root: Path, pid: str, state: str = "CLOSING_PRODUCED") -> None:
    base = root / "projects" / pid
    (base / "meta").mkdir(parents=True, exist_ok=True)
    (base / "chart").mkdir(exist_ok=True)
    (base / "chart" / "HarnessFlowGoal.md").write_text("# Goal", encoding="utf-8")
    (base / "meta" / "state.json").write_text(
        json.dumps({"state": state, "project_id": pid}), encoding="utf-8",
    )


class TestL2_06_ProduceClosing:

    def test_TC_L102_L206_produce_closing_3_md(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        _setup_draft_project(tmp_project_root, pid, state="INITIALIZED")
        result: ClosingResult = sut.produce_closing(
            pid, project_root=str(tmp_project_root),
        )
        assert Path(result.lessons_path).exists()
        assert Path(result.manifest_path).exists()
        assert Path(result.retro_path).exists()
        assert len(result.closing_bundle_hash) == 64

    def test_TC_L102_L206_pm14_ownership_violation(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        with pytest.raises(ClosingError) as exc:
            sut.produce_closing(
                pid, project_root=str(tmp_project_root), caller_l2="L2-03",
            )
        assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION

    def test_TC_L102_L206_upstream_not_ready(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        """state.json 不存在 · E_UPSTREAM_NOT_READY。"""
        with pytest.raises(ClosingError) as exc:
            sut.produce_closing(pid, project_root=str(tmp_project_root))
        assert exc.value.error_code == E_UPSTREAM_NOT_READY


class TestL2_06_ArchiveProject:

    def test_TC_L102_L206_archive_creates_tar_zst(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        _setup_draft_project(tmp_project_root, pid)
        manifest: ArchiveManifest = sut.archive_project(
            pid, project_root=str(tmp_project_root),
        )
        assert Path(manifest.archive_path).exists()
        assert manifest.archive_path.endswith(".tar.zst")
        # sha256 复验
        import hashlib
        actual_sha = hashlib.sha256(Path(manifest.archive_path).read_bytes()).hexdigest()
        assert actual_sha == manifest.sha256
        assert manifest.size_bytes > 0

    def test_TC_L102_L206_archive_chmod_0444(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        """归档后源文件 chmod 0444 · 写入应拒。"""
        _setup_draft_project(tmp_project_root, pid)
        sut.archive_project(pid, project_root=str(tmp_project_root))
        # 尝试写入 chart 文件应失败（只读）
        chart_path = tmp_project_root / "projects" / pid / "chart" / "HarnessFlowGoal.md"
        import stat
        mode = chart_path.stat().st_mode
        assert (mode & 0o777) == 0o444, f"expected 0444 got {oct(mode & 0o777)}"

    def test_TC_L102_L206_archive_pm14_violation(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        _setup_draft_project(tmp_project_root, pid)
        with pytest.raises(ClosingError) as exc:
            sut.archive_project(
                pid, project_root=str(tmp_project_root), caller_l2="L2-05",
            )
        assert exc.value.error_code == E_PM14_OWNERSHIP_VIOLATION

    def test_TC_L102_L206_archive_state_not_closing_approved(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        _setup_draft_project(tmp_project_root, pid, state="PLANNING")
        with pytest.raises(ClosingError) as exc:
            sut.archive_project(pid, project_root=str(tmp_project_root))
        assert exc.value.error_code == E_STATE_NOT_CLOSING_APPROVED


class TestL2_06_PurgeProject:

    def test_TC_L102_L206_purge_too_early(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        """归档后 0 天立即 purge · E_PURGE_TOO_EARLY。"""
        _setup_draft_project(tmp_project_root, pid)
        sut.archive_project(pid, project_root=str(tmp_project_root))
        token = f"PURGE-{pid}-CONFIRMED"
        with pytest.raises(ClosingError) as exc:
            sut.purge_project(
                pid, project_root=str(tmp_project_root), confirm_token=token,
            )
        assert exc.value.error_code == E_PURGE_TOO_EARLY

    def test_TC_L102_L206_purge_token_mismatch(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        _setup_draft_project(tmp_project_root, pid)
        sut.archive_project(pid, project_root=str(tmp_project_root))
        with pytest.raises(ClosingError) as exc:
            sut.purge_project(
                pid, project_root=str(tmp_project_root), confirm_token="WRONG-TOKEN",
            )
        assert exc.value.error_code == E_PURGE_TOKEN_MISMATCH

    def test_TC_L102_L206_purge_success_after_90_days(
        self, sut: ClosingExecutor, pid: str, tmp_project_root: Path,
    ) -> None:
        """模拟归档 91 天前 · purge 成功。"""
        _setup_draft_project(tmp_project_root, pid)
        sut.archive_project(pid, project_root=str(tmp_project_root))
        # 篡改 archive manifest 的 archived_at · 模拟 91 天前
        manifest_json = (
            tmp_project_root / "projects" / "_archive" / f"{pid}.manifest.json"
        )
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        old_date = datetime.now(timezone.utc) - timedelta(days=91)
        data["archived_at"] = old_date.isoformat()
        manifest_json.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

        token = f"PURGE-{pid}-CONFIRMED"
        result: PurgeResult = sut.purge_project(
            pid, project_root=str(tmp_project_root), confirm_token=token,
        )
        assert result.purged is True
        assert not (tmp_project_root / "projects" / pid).exists()
        assert not manifest_json.exists()
