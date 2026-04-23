"""L1-05 测试局部 fixtures · 导出 4 个 mock 单例 + 通用临时项目根目录.

这些 fixtures 不暴露到 tests/ 根 · 避免干扰 Dev-α/β/δ 的测试套件。
"""
from __future__ import annotations

import pathlib
import uuid
from collections.abc import Iterator

import pytest

from app.skill_dispatch._mocks.dod_gate_mock import DoDGateMock
from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
from app.skill_dispatch._mocks.ic09_mock import IC09EventBusMock
from app.skill_dispatch._mocks.lock_mock import AccountLockMock


@pytest.fixture
def tmp_project(tmp_path: pathlib.Path) -> Iterator[pathlib.Path]:
    """构造一个 mock 的 `projects/<pid>/` 根目录 · 自动清理.

    目录结构符合 PM-14 物理分片：
        <pid>/
          skills/registry-cache/
          events/
    """
    pid = f"proj_{uuid.uuid4().hex[:8]}"
    root = tmp_path / "projects" / pid
    (root / "skills" / "registry-cache").mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir(parents=True, exist_ok=True)
    yield root


@pytest.fixture
def fake_pid() -> str:
    return f"proj_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def ic09_bus() -> Iterator[IC09EventBusMock]:
    bus = IC09EventBusMock()
    yield bus
    bus.flush()


@pytest.fixture
def kb_mock() -> IC06KBMock:
    return IC06KBMock()


@pytest.fixture
def lock_mock() -> AccountLockMock:
    return AccountLockMock()


@pytest.fixture
def dod_gate() -> DoDGateMock:
    return DoDGateMock()


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"
