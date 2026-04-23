"""L1-02 跨 L2 共享测试 fixture（所有 WP 共用）。

WP01 / WP02 等在各自 test 文件中扩充本 conftest 的 fixture（本文件只放跨 WP 共享的）。
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.l1_02.common.event_emitter import EventEmitter


_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _make_ulid_like() -> str:
    """生成 ULID-格式（26 char）字符串 · 仅用于测试 · 非真实时间戳。"""
    raw = uuid.uuid4().bytes
    return "".join(_CROCKFORD_BASE32[b % 32] for b in raw)[:26].ljust(26, "0")


@pytest.fixture
def mock_project_id() -> str:
    """ULID 格式 pid · 每 test 唯一。"""
    return _make_ulid_like()


@pytest.fixture
def mock_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def mock_event_bus() -> EventEmitter:
    return EventEmitter()


@pytest.fixture
def tmp_projects_root(tmp_path: Path) -> Path:
    """隔离 projects/ 根 · PM-14 相关测试用。"""
    root = tmp_path / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def template_dir_real() -> Path:
    """指向仓库根 templates/ 的真实模板目录。"""
    return Path(__file__).resolve().parent.parent.parent / "templates"
