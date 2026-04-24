"""IC-04 集成测试 fixtures · 真实 SkillExecutor / IntentSelector / Registry.

铁律: 真实 import L1-05 skill_dispatch 模块 · 只 mock 跨进程/API 边界.
    - IntentSelector · 真实
    - RegistryQueryAPI · 真实 (从 fixture yaml 加载)
    - SkillExecutor · 真实
    - skill_runner · 测试替身 (各 TC 按需构造)
"""
from __future__ import annotations

import pathlib
import shutil
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from app.skill_dispatch._mocks.ic06_mock import IC06KBMock
from app.skill_dispatch._mocks.ic09_mock import IC09EventBusMock
from app.skill_dispatch._mocks.lock_mock import AccountLockMock
from app.skill_dispatch.intent_selector import IntentSelector
from app.skill_dispatch.invoker.executor import SkillExecutor
from app.skill_dispatch.registry.ledger import LedgerWriter
from app.skill_dispatch.registry.loader import RegistryLoader
from app.skill_dispatch.registry.query_api import RegistryQueryAPI


@pytest.fixture
def wp02_fixtures_dir() -> pathlib.Path:
    """复用已有 skill_dispatch fixtures (registry_valid.yaml)."""
    return pathlib.Path(__file__).parents[2] / "skill_dispatch" / "fixtures"


@pytest.fixture
def project_id() -> str:
    """IC-04 TC 默认 pid · 符合 PM-14 `[a-z0-9_-]{1,40}` pattern."""
    return f"proj_wp02_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def tmp_project(tmp_path: pathlib.Path, project_id: str) -> Iterator[pathlib.Path]:
    """构造 PM-14 物理分片根目录 · skills/registry-cache + events/."""
    root = tmp_path / "projects" / project_id
    (root / "skills" / "registry-cache").mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir(parents=True, exist_ok=True)
    yield root


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


SkillRunnerFactory = Callable[..., Callable[..., dict[str, Any]]]


@pytest.fixture
def make_executor(
    tmp_project: pathlib.Path,
    wp02_fixtures_dir: pathlib.Path,
    ic09_bus: IC09EventBusMock,
    kb_mock: IC06KBMock,
    lock_mock: AccountLockMock,
):
    """工厂 · 传入 skill_runner callable · 返完整装配的真实 SkillExecutor."""

    def _make(skill_runner) -> SkillExecutor:
        cache = tmp_project / "skills" / "registry-cache"
        shutil.copy(wp02_fixtures_dir / "registry_valid.yaml", cache / "registry.yaml")
        snap = RegistryLoader(project_root=tmp_project).load()
        api = RegistryQueryAPI(snapshot=snap)
        selector = IntentSelector(registry=api, event_bus=ic09_bus, kb=kb_mock)
        ledger = LedgerWriter(project_root=tmp_project, lock=lock_mock)
        return SkillExecutor(
            selector=selector,
            event_bus=ic09_bus,
            ledger=ledger,
            skill_runner=skill_runner,
        )

    return _make
