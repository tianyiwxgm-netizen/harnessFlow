"""IC-19 集成 fixtures · 真实 build_push_stage_gate_card_command + UIBridge.

WP04 任务表 IC-19 = ui_card_push (L1-10 UI 卡片 · 对应 ic-contracts.md §3.16
push_stage_gate_card).
"""
from __future__ import annotations

from typing import Any

import pytest

from app.project_lifecycle.stage_gate.ic_16_stub import (
    UIBridge,
    build_push_stage_gate_card_command,
)


@pytest.fixture
def project_id() -> str:
    return "proj-ic19"


class FakeUIBridge:
    """L1-10 UI bridge 假实现 · 记录所有 push command."""

    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.exc_to_raise: Exception | None = None

    def push_stage_gate_card_to_ui(
        self, *, command: dict[str, Any],
    ) -> dict[str, Any]:
        if self.exc_to_raise is not None:
            raise self.exc_to_raise
        self.received.append(dict(command))
        return {"received": True, "card_id": command.get("card_id")}


class FakeAuditBus:
    """L1-09 audit bus 替身 · 记录 IC-09 落盘."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append_event(
        self,
        *,
        project_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.events.append({
            "project_id": project_id,
            "event_type": event_type,
            "payload": dict(payload),
        })


@pytest.fixture
def ui_bridge() -> FakeUIBridge:
    return FakeUIBridge()


@pytest.fixture
def audit_bus() -> FakeAuditBus:
    return FakeAuditBus()
