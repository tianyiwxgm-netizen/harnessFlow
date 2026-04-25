"""IC-11 集成 fixtures · LockManager.release_lock 路径."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.lock_manager.manager import LockManager


@pytest.fixture
def project_id() -> str:
    return "proj-ic11"


@pytest.fixture
def lock_root(tmp_path: Path) -> Path:
    root = tmp_path / "lock_workdir"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def lock_manager(lock_root: Path) -> LockManager:
    return LockManager(workdir=lock_root)


@pytest.fixture
def make_resource(project_id: str):
    def _make(rtype: str = "task_board", pid: str | None = None) -> str:
        return f"{pid or project_id}:{rtype}"

    return _make


@pytest.fixture
def make_holder():
    def _make(l1: str = "L1-04", sub: str = "verifier", ctx: str = "") -> str:
        return f"{l1}:{sub}" + (f":{ctx}" if ctx else "")

    return _make
