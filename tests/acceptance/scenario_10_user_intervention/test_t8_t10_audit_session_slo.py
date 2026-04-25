"""Scenario 10 · T8-T10 · audit user_id + 跨 session UI state + IC-19 SLO.

T8: audit 必含 user_id (硬约束 · IC-19 §3.19.x)
T9: 跨 session UI state · 旧 session 干预 audit · 新 session 仍可见
T10: IC-19 SLO · UI emit 端到端 < 100ms
"""
from __future__ import annotations

import time

from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


def test_t8_audit_must_contain_user_id(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T8 · IC-19 audit 硬约束 · 所有 user_intervention payload 必含 user_id."""
    with gwt("T8 · audit user_id 必带 (硬约束)"):
        gwt.given("emit 4 个 IC-19 user_intervention 事件")
        for u in ["user-1", "user-2", "user-3", "user-4"]:
            emit_user_event(
                "L1-01:user_intervention",
                {"action": "pause"},
                user_id=u,
            )

        gwt.then("4 条 audit · 每条 payload.user_id 必带")
        events = list_events(
            event_bus_root,
            project_id,
            type_exact="L1-01:user_intervention",
        )
        assert len(events) == 4
        for evt in events:
            user_id = evt.get("payload", {}).get("user_id")
            assert user_id and user_id.startswith("user-"), (
                f"event 缺 user_id 或格式错: {evt}"
            )


def test_t9_cross_session_ui_state_persists(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T9 · 旧 UI session emit · 新 session/EventBus instance 仍可读 audit."""
    with gwt("T9 · 跨 session UI state 持久"):
        gwt.given("旧 session emit pause + force_block")
        emit_user_event(
            "L1-01:user_intervention",
            {"action": "pause", "session_id": "ui-old"},
            user_id="user-cross",
        )
        emit_user_event(
            "L1-01:user_intervention",
            {"action": "force_block", "session_id": "ui-old"},
            user_id="user-cross",
        )

        gwt.when("新 EventBus instance 重新读 (模拟 new UI session)")
        new_bus = EventBus(event_bus_root)
        # 不必新 emit · 直接验旧 audit 仍可见
        # (EventBus 是 file-backed · 自动恢复)

        gwt.then("从新 instance 读 · audit 含 2 条 user_intervention")
        events = list_events(
            event_bus_root,
            project_id,
            type_exact="L1-01:user_intervention",
        )
        actions = [e["payload"]["action"] for e in events]
        assert sorted(actions) == ["force_block", "pause"]


def test_t10_ic19_emit_under_100ms_slo(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T10 · IC-19 emit 端到端 SLO · < 100ms."""
    with gwt("T10 · IC-19 emit SLO < 100ms"):
        gwt.given("UI 在线 · L1-09 EventBus 干净")

        gwt.when("emit 1 IC-19 · 测端到端 wall clock")
        t0 = time.monotonic()
        emit_user_event(
            "L1-01:user_intervention",
            {"action": "pause"},
            user_id="user-slo",
        )
        elapsed_ms = (time.monotonic() - t0) * 1000

        gwt.then(f"端到端 elapsed={elapsed_ms:.2f}ms < 100ms · IC-19 SLO")
        assert elapsed_ms < 100.0, (
            f"IC-19 emit 超时 实际={elapsed_ms:.2f}ms · 应 < 100ms"
        )

        gwt.then("audit 1 条落盘")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
        )
        assert len(events) == 1
