"""Scenario 10 · UI 干预 fixtures · 真实 HaltEnforcer + L1-09 EventBus.

UI 干预 = 通过 IC-19 把 user 操作打入 L1-01/L2-XX · 直接断 audit 落 user_id.
HaltEnforcer.pause/resume 模拟暂停/恢复.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.schemas import TickState
from tests.shared.gwt_helpers import gwt  # noqa: F401


@pytest.fixture
def project_id() -> str:
    """Scenario 10 用 pid · L1-09 严格 ^[a-z0-9_-]{1,40}$."""
    return "proj-acc10-user-ui"


@pytest.fixture
def event_bus_root(tmp_path: Path) -> Path:
    root = tmp_path / "bus_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def real_event_bus(event_bus_root: Path) -> EventBus:
    return EventBus(event_bus_root)


@pytest.fixture
def halt_enforcer(project_id: str) -> HaltEnforcer:
    """L1-01 HaltEnforcer · 用于暂停/恢复测试."""
    return HaltEnforcer(project_id=project_id)


@pytest.fixture
def emit_user_event(real_event_bus: EventBus, project_id: str):
    """工厂 · 模拟 IC-19 user_intervention emit · audit 必带 user_id."""

    def _emit(
        event_type: str,
        payload: dict,
        user_id: str = "user-default",
    ) -> str:
        # IC-19 user 操作必带 user_id (audit 闭环)
        merged = dict(payload)
        merged.setdefault("user_id", user_id)
        evt = Event(
            project_id=project_id,
            type=event_type,
            actor="ui",
            timestamp=datetime.now(UTC),
            payload=merged,
        )
        return real_event_bus.append(evt).event_id

    return _emit


# UI 干预合法操作集 (IC-19 §3.19.x)
UI_OPERATIONS: tuple[str, ...] = (
    "pause",
    "resume",
    "modify_dod",
    "skip_wp",
    "force_block",
)
