"""PM-14 隔离测试 fixtures · 真实 EventBus + 双 project_id.

继承 tests/shared/ fixture · 本 conftest 仅补:
    - two_pids: 两个独立 pid (A/B) · 物理 events.jsonl 各自分片
    - make_l1_event: 简化 Event 构造器(默认合法字段)
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event

# Re-export tests/shared/conftest fixtures so this dir can use them
from tests.shared.conftest import (  # noqa: F401
    audit_sink,
    callback_waiter,
    ckpt_root,
    delegate_stub,
    event_bus_root,
    fake_kb_repo,
    fake_llm,
    fake_reranker,
    fake_scope_checker,
    fake_skill_invoker,
    fake_tool_client,
    kb_root,
    lock_root,
    no_sleep,
    other_project_id,
    project_id,
    projects_root,
    real_event_bus,
    state_spy,
    tmp_root,
)


@pytest.fixture
def two_pids() -> tuple[str, str]:
    """A / B 双 pid · PM-14 跨分片隔离场景默认对.

    用法:
        pid_a, pid_b = two_pids
        # 写 pid_a 的事件
        # 断言 pid_b 分片为空
    """
    return ("proj-iso-a", "proj-iso-b")


@pytest.fixture
def make_l1_event():
    """构造合法 IC-09 Event · 默认字段齐 · 可覆盖关键字段."""

    def _mk(
        *,
        project_id: str,
        event_type: str = "L1-04:verifier_report_issued",
        actor: str = "verifier",
        payload: dict[str, Any] | None = None,
    ) -> Event:
        return Event(
            project_id=project_id,
            type=event_type,
            actor=actor,
            payload=dict(payload or {}),
            timestamp=datetime.now(UTC),
        )

    return _mk


@pytest.fixture
def write_event_to(real_event_bus: EventBus, make_l1_event):
    """快捷封装: 给 pid 写一条事件 · 返回 AppendEventResult."""

    def _write(
        pid: str,
        *,
        event_type: str = "L1-04:verifier_report_issued",
        actor: str = "verifier",
        payload: dict[str, Any] | None = None,
    ):
        evt = make_l1_event(
            project_id=pid,
            event_type=event_type,
            actor=actor,
            payload=payload,
        )
        return real_event_bus.append(evt)

    return _write
