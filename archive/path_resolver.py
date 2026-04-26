"""v1.7 fix defects #6 — harnessFlow 默认 task-board 路径解析歧义.

根因：主 skill § 2.1 文字 `harnessFlow /task-boards/<task_id>.json` 末尾带空格，
LLM 在 skill 加载环境（`~/.claude/skills/harnessFlow/` 或 plugins cache）下
解析为相对子目录，与 UI 读取的 repo 路径
`/Users/zhongtianyi/work/code/harnessFlow/task-boards/` 不一致 → bootstrap
新建的 task-board 在 UI 看不到。

修复：定义 `resolve_task_boards_dir()` 单一权威入口，按以下优先级返绝对
`Path`，所有写入端必须经过：

1. `HARNESSFLOW_DIR` 环境变量（覆盖一切，主用于测试）
2. `git rev-parse --show-toplevel` 找 repo root，拼 `harnessFlow/task-boards/`
3. 兜底常量绝对路径 `/Users/zhongtianyi/work/code/harnessFlow/task-boards/`

注：harnessFlow repo 本身已经被 clone 到 `<work>/harnessFlow/`，所以从
该 repo 内任何子目录跑 git rev-parse 都返 repo root，再拼 `task-boards/`。
若主 skill 被加载到 `~/.claude/plugins/cache/...` 这种非 git 环境（git
rev-parse 失败），就退到第 3 步绝对路径。

DEFAULT_HARNESSFLOW_REPO_ROOT 是写死的本地 fallback —— 主用户 zhongtianyi
的工作目录；其他用户必须设 `HARNESSFLOW_DIR` 环境变量。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

DEFAULT_HARNESSFLOW_REPO_ROOT = Path("/Users/zhongtianyi/work/code/harnessFlow")


def resolve_harnessflow_root() -> Path:
    """返回 harnessFlow repo 根的绝对 Path（含 task-boards / retros / 等）。

    优先级：HARNESSFLOW_DIR env > git rev-parse > DEFAULT_HARNESSFLOW_REPO_ROOT
    """
    env = os.environ.get("HARNESSFLOW_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        repo_root = Path(out.stdout.strip()).resolve()
        # 仅当 repo root 名字为 harnessFlow 才认为在本仓库（防误用其他 repo cwd）
        if repo_root.name == "harnessFlow" and repo_root.exists():
            return repo_root
        # 若在 harnessFlow 子目录被 git 当成另一 repo（极端 worktree 场景），
        # 用 cwd 向上找 harnessFlow 文件夹
        for ancestor in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
            if ancestor.name == "harnessFlow" and ancestor.exists():
                return ancestor
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 兜底：写死的绝对路径（DEFAULT_HARNESSFLOW_REPO_ROOT）
    if DEFAULT_HARNESSFLOW_REPO_ROOT.exists():
        return DEFAULT_HARNESSFLOW_REPO_ROOT
    raise FileNotFoundError(
        "Cannot resolve harnessFlow root: HARNESSFLOW_DIR not set, "
        "git rev-parse failed, and DEFAULT_HARNESSFLOW_REPO_ROOT does not exist. "
        f"Tried: {DEFAULT_HARNESSFLOW_REPO_ROOT}"
    )


def resolve_task_boards_dir() -> Path:
    """task-boards/ 目录绝对 Path。bootstrap / writer / UI 后端唯一入口。"""
    return resolve_harnessflow_root() / "task-boards"


def resolve_retros_dir() -> Path:
    return resolve_harnessflow_root() / "retros"


def resolve_supervisor_events_dir() -> Path:
    return resolve_harnessflow_root() / "supervisor-events"


def resolve_failure_archive_path() -> Path:
    return resolve_harnessflow_root() / "failure-archive.jsonl"


def resolve_task_board_path(task_id: str) -> Path:
    """`<repo_root>/harnessFlow/task-boards/<task_id>.json` 的绝对 Path。"""
    if not task_id or "/" in task_id or "\\" in task_id:
        raise ValueError(f"invalid task_id: {task_id!r}")
    return resolve_task_boards_dir() / f"{task_id}.json"
