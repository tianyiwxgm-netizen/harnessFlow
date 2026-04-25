"""IC-10 集成 fixtures · 真实 LockManager · acquire_lock 路径.

WP04 任务表 IC-10 = lock_acquire (L1-09 LockManager 内部 IC).
铁律: 真实 import LockManager · flock + FIFO + deadlock 全链.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.lock_manager.manager import LockManager


@pytest.fixture
def project_id() -> str:
    return "proj-ic10"


@pytest.fixture
def lock_root(tmp_path: Path) -> Path:
    """每 TC 独立物理根 · LockManager 在此下建 tmp/projects."""
    root = tmp_path / "lock_workdir"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def lock_manager(lock_root: Path) -> LockManager:
    """真实 L1-09 LockManager · workdir = tmp_path."""
    return LockManager(workdir=lock_root)


@pytest.fixture
def make_resource(project_id: str):
    """工厂 · 合法 resource_name (`<pid>:<type>`)."""

    def _make(rtype: str = "task_board", pid: str | None = None) -> str:
        return f"{pid or project_id}:{rtype}"

    return _make


@pytest.fixture
def make_holder():
    """工厂 · 合法 holder (`<L-id>:<sub>[:<ctx>]`)."""

    def _make(l1: str = "L1-04", sub: str = "verifier", ctx: str = "") -> str:
        if ctx:
            return f"{l1}:{sub}:{ctx}"
        return f"{l1}:{sub}"

    return _make
