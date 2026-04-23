"""共享 fixture — Dev-α L1-09 测试（对齐 §10.2）."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_fs(tmp_path: Path) -> Generator[Path, None, None]:
    """临时文件系统沙箱（每测试独立 · pytest tmp_path 自动清理）."""
    root = tmp_path / "harness_fs"
    root.mkdir(parents=True, exist_ok=True)
    yield root


@pytest.fixture
def mock_project_id() -> str:
    """生成 PM-14 合规的 project_id（短 uuid · snake_case 可读）."""
    return f"proj-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def another_project_id() -> str:
    """第二个 project_id · PM-14 隔离测试用."""
    return f"proj-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> Generator[list[float], None, None]:
    """可控时钟 · 测试 fsync 延迟 / TTL 泄漏 / timeout 用."""
    t = [1700000000.0]

    def advance(secs: float) -> None:
        t[0] += secs

    monkeypatch.setattr(time, "time", lambda: t[0])
    monkeypatch.setattr(time, "monotonic", lambda: t[0])
    yield t  # tests 可通过 t[0] += n 前进时间


@pytest.fixture
def disk_full_mock(monkeypatch: pytest.MonkeyPatch):
    """模拟 ENOSPC · 供 atomic_writer / append 测试."""
    original_write = os.write

    class State:
        trigger: bool = False

    def fake_write(fd: int, data: bytes) -> int:
        if State.trigger:
            raise OSError(28, "No space left on device (mocked)")
        return original_write(fd, data)

    monkeypatch.setattr(os, "write", fake_write)
    return State


@pytest.fixture
def fsync_fail_mock(monkeypatch: pytest.MonkeyPatch):
    """模拟 fsync EIO · L1-09 halt 触发测试核心 fixture."""
    class State:
        trigger: bool = False
        count: int = 0

    original_fsync = os.fsync

    def fake_fsync(fd: int) -> None:
        State.count += 1
        if State.trigger:
            raise OSError(5, "Input/output error (mocked fsync EIO)")
        return original_fsync(fd)

    monkeypatch.setattr(os, "fsync", fake_fsync)
    return State


@pytest.fixture
def isolated_tmpdir() -> Generator[Path, None, None]:
    """独立 tmpdir · 用于非 pytest tmp_path 场景（如 perf bench）."""
    path = Path(tempfile.mkdtemp(prefix="harness_test_"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
