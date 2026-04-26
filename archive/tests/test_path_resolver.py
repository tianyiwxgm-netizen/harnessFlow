"""v1.7 fix defects #6 — archive.path_resolver 单测.

cover：
- HARNESSFLOW_DIR env 覆盖一切
- 在 git repo 内（rev-parse 成功 + repo name=harnessFlow） → 返 repo root
- 在 git repo 内但 repo name ≠ harnessFlow → 走 cwd ancestor 兜底
- env 不存在 / git 失败 → DEFAULT 兜底
- 派生路径 4 个（task_boards / retros / supervisor_events / failure_archive）
- resolve_task_board_path 拼接 + 拒非法 task_id
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from archive import path_resolver


HARNESS_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---- env override 优先 ---------------------------------------------------- #


def test_env_override_wins(monkeypatch, tmp_path) -> None:
    fake_root = tmp_path / "fake_harnessflow"
    fake_root.mkdir()
    monkeypatch.setenv("HARNESSFLOW_DIR", str(fake_root))
    out = path_resolver.resolve_harnessflow_root()
    assert out == fake_root.resolve()


def test_env_override_nonexistent_falls_through(monkeypatch, tmp_path) -> None:
    """env 设了但路径不存在 → 不算数，继续往下找."""
    monkeypatch.setenv("HARNESSFLOW_DIR", str(tmp_path / "does_not_exist"))
    # 当前 cwd 在 harnessFlow repo 内 → git 兜底成功
    out = path_resolver.resolve_harnessflow_root()
    assert out.name == "harnessFlow"


# ---- git rev-parse 兜底（real, in-repo） ---------------------------------- #


def test_git_rev_parse_returns_harnessflow_root(monkeypatch) -> None:
    monkeypatch.delenv("HARNESSFLOW_DIR", raising=False)
    out = path_resolver.resolve_harnessflow_root()
    assert out.name == "harnessFlow"
    assert (out / "harnessFlow-skill.md").exists()


def test_git_rev_parse_wrong_repo_falls_to_default(monkeypatch, tmp_path) -> None:
    """git rev-parse 返一个不是 harnessFlow 的 repo → 用 default 绝对路径兜底."""
    monkeypatch.delenv("HARNESSFLOW_DIR", raising=False)

    fake_other_repo = type("R", (), {})()
    fake_completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="/some/other/repo\n", stderr=""
    )
    with patch.object(subprocess, "run", return_value=fake_completed):
        with patch.object(Path, "cwd", return_value=tmp_path):  # cwd 也不在 harnessFlow
            out = path_resolver.resolve_harnessflow_root()
    # 落到 DEFAULT
    assert out == path_resolver.DEFAULT_HARNESSFLOW_REPO_ROOT


def test_git_failure_falls_to_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("HARNESSFLOW_DIR", raising=False)
    with patch.object(subprocess, "run", side_effect=FileNotFoundError("no git")):
        with patch.object(Path, "cwd", return_value=tmp_path):
            out = path_resolver.resolve_harnessflow_root()
    assert out == path_resolver.DEFAULT_HARNESSFLOW_REPO_ROOT


# ---- 派生路径 ------------------------------------------------------------- #


def test_resolve_task_boards_dir(monkeypatch) -> None:
    monkeypatch.setenv("HARNESSFLOW_DIR", str(HARNESS_REPO_ROOT))
    out = path_resolver.resolve_task_boards_dir()
    assert out == HARNESS_REPO_ROOT / "task-boards"
    assert out.exists()


def test_resolve_retros_dir(monkeypatch) -> None:
    monkeypatch.setenv("HARNESSFLOW_DIR", str(HARNESS_REPO_ROOT))
    out = path_resolver.resolve_retros_dir()
    assert out == HARNESS_REPO_ROOT / "retros"


def test_resolve_supervisor_events_dir(monkeypatch) -> None:
    monkeypatch.setenv("HARNESSFLOW_DIR", str(HARNESS_REPO_ROOT))
    out = path_resolver.resolve_supervisor_events_dir()
    assert out == HARNESS_REPO_ROOT / "supervisor-events"


def test_resolve_failure_archive_path(monkeypatch) -> None:
    monkeypatch.setenv("HARNESSFLOW_DIR", str(HARNESS_REPO_ROOT))
    out = path_resolver.resolve_failure_archive_path()
    assert out == HARNESS_REPO_ROOT / "failure-archive.jsonl"


# ---- task_board_path 拼接 ------------------------------------------------- #


def test_resolve_task_board_path_builds_filename(monkeypatch) -> None:
    monkeypatch.setenv("HARNESSFLOW_DIR", str(HARNESS_REPO_ROOT))
    out = path_resolver.resolve_task_board_path("p-foo-20260426T180000Z")
    assert out == HARNESS_REPO_ROOT / "task-boards" / "p-foo-20260426T180000Z.json"


def test_resolve_task_board_path_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        path_resolver.resolve_task_board_path("../etc/passwd")
    with pytest.raises(ValueError):
        path_resolver.resolve_task_board_path("a/b")
    with pytest.raises(ValueError):
        path_resolver.resolve_task_board_path("")
