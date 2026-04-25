"""Scenario 10 · T5-T7 · UI offline + 多 user 并发 + 越权拒绝.

T5: UI offline · 操作进队列待发 (audit emit 不依赖 UI live)
T6: 多 user 并发 · 各 emit 互不串
T7: 越权拒 · user 无权限 · audit 含 unauthorized 标志
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


def test_t5_ui_offline_queue_pending(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T5 · UI offline · audit 仍 emit · queue_pending 标志."""
    with gwt("T5 · UI offline 队列待发"):
        gwt.given("UI offline · backend 仍能接 IC-19 (有 queue)")

        gwt.when("emit ui_offline_intervention · queue_pending=True")
        emit_user_event(
            "L1-01:user_intervention",
            {
                "action": "pause",
                "ui_state": "offline",
                "queue_pending": True,
            },
            user_id="user-offline",
        )

        gwt.then("audit 落 · 含 queue_pending 标志")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
            payload_contains={"queue_pending": True, "action": "pause"},
        )
        assert len(events) == 1


def test_t6_multi_user_concurrent_intervention(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T6 · 3 user 并发 emit · audit 各落 · user_id 不串."""
    with gwt("T6 · 多 user 并发"):
        gwt.given("3 user (alice/bob/charlie) 同时干预")

        gwt.when("3 user 各 emit IC-19")
        for u in ["user-alice", "user-bob", "user-charlie"]:
            emit_user_event(
                "L1-01:user_intervention",
                {"action": "pause", "intent": f"intent-{u}"},
                user_id=u,
            )

        gwt.then("3 条 audit · 各 user_id 独立")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
            min_count=3,
        )
        users = {e["payload"]["user_id"] for e in events}
        assert users == {"user-alice", "user-bob", "user-charlie"}

        gwt.then("hash chain 串行 · seq=1..3")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 3


def test_t7_unauthorized_user_rejected(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T7 · 越权 user · audit 标 unauthorized=True."""
    with gwt("T7 · 越权拒"):
        gwt.given("user-attacker 无 release 权限")

        gwt.when("user-attacker 尝试 force_block · 系统拒并 audit unauthorized")
        emit_user_event(
            "L1-01:user_intervention_rejected",
            {
                "action": "force_block",
                "reason": "insufficient_permission",
                "unauthorized": True,
            },
            user_id="user-attacker",
        )

        gwt.then("audit 含 unauthorized=True · user_id=user-attacker")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention_rejected",
            payload_contains={
                "unauthorized": True,
                "user_id": "user-attacker",
            },
        )
        assert len(events) == 1
