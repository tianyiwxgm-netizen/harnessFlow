"""E-2 P2 · read_range 空 project 行为分治.

修复前：空 project（dir 存在但 events.jsonl 未生成）也 raise BusProjectNotRegistered
修复后：
- events.jsonl 不存在 + project_dir 不存在 → BusProjectNotRegistered（未注册）
- events.jsonl 不存在 + project_dir 存在 → 空 iterator（空 project）
- events.jsonl 存在 → 正常流式
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus import BusProjectNotRegistered, EventBus
from app.l1_09.event_bus.reader import read_range


def test_TC_E2_empty_dir_returns_empty_iter(tmp_fs: Path) -> None:
    """E-2 fix: project_dir 存在但 events.jsonl 不存在 · 返空 iterator（非 raise）."""
    project_dir = tmp_fs / "projects" / "proj-empty"
    project_dir.mkdir(parents=True)
    events_path = project_dir / "events.jsonl"

    # events 不存在 · 但 dir 在 → 空 iter
    result = list(read_range(events_path, project_dir=project_dir))
    assert result == []


def test_TC_E2_missing_dir_still_raises(tmp_fs: Path) -> None:
    """E-2 fix 不回归：dir 和 events 都不存在 → raise BusProjectNotRegistered."""
    events_path = tmp_fs / "projects" / "proj-ghost" / "events.jsonl"

    with pytest.raises(BusProjectNotRegistered):
        list(read_range(events_path))


def test_TC_E2_legacy_signature_still_raises(tmp_fs: Path) -> None:
    """E-2 fix 向后兼容：不传 project_dir · 保持 raise（向后兼容）."""
    events_path = tmp_fs / "nonexistent" / "events.jsonl"

    with pytest.raises(BusProjectNotRegistered):
        list(read_range(events_path))


def test_TC_E2_bus_read_range_empty_project_returns_empty(tmp_fs: Path) -> None:
    """E-2 fix: EventBus.read_range 空 project（register 后 · 未 append）· 返空."""
    bus = EventBus(root=tmp_fs)
    # 手工创建 project_dir（模拟 register 但还没 append）
    pid = "proj-empty-12345"
    (tmp_fs / "projects" / pid).mkdir(parents=True)

    result = list(bus.read_range(pid))
    assert result == []


def test_TC_E2_bus_read_range_unregistered_raises(tmp_fs: Path) -> None:
    """E-2 fix 回归：完全没创建 · 仍 raise."""
    bus = EventBus(root=tmp_fs)
    with pytest.raises(BusProjectNotRegistered):
        list(bus.read_range("proj-nonexistent-999"))
