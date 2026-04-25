"""Scenario 10 · T1-T4 · 暂停/恢复 + 修改 DoD + 跳过 WP + 强制 BLOCK.

T1: 暂停/恢复 · HaltEnforcer 翻 PAUSED → RUNNING
T2: 修改 DoD · 运行时 hot reload · audit 含 dod_changed
T3: 跳过 WP · user 显式授权 · audit 含 skip_wp
T4: 强制 BLOCK · user 发 IC-19 + halt → audit 含 force_block
"""
from __future__ import annotations

from app.l1_09.event_bus.core import EventBus
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.schemas import TickState
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_emitted


def test_t1_pause_resume_via_ui(
    project_id: str,
    halt_enforcer: HaltEnforcer,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T1 · UI 暂停/恢复 · HaltEnforcer 翻 PAUSED → RUNNING + audit 落 user_id."""
    with gwt("T1 · UI 暂停/恢复"):
        gwt.given(f"halt_enforcer 初态 RUNNING")
        assert halt_enforcer.as_tick_state() == TickState.RUNNING

        gwt.when("user 在 UI 点 pause · IC-19 emit user_pause")
        emit_user_event(
            "L1-01:user_intervention",
            {"action": "pause", "ui_session_id": "ui-1"},
            user_id="user-alice",
        )

        gwt.then("audit 含 user_pause + user_id=alice")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
            payload_contains={"action": "pause", "user_id": "user-alice"},
        )
        assert len(events) == 1

        gwt.when("user 再 emit resume")
        emit_user_event(
            "L1-01:user_intervention",
            {"action": "resume", "ui_session_id": "ui-1"},
            user_id="user-alice",
        )

        gwt.then("audit 含 resume 事件")
        resume_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
            payload_contains={"action": "resume"},
        )
        assert len(resume_events) == 1


def test_t2_modify_dod_hot_reload(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T2 · 修改 DoD 运行时 · audit 含 dod_old / dod_new + user 授权."""
    with gwt("T2 · 修改 DoD 热加载"):
        gwt.given("DoD 当前 'lint+typecheck'")

        gwt.when("user 修改为 'lint+typecheck+e2e'")
        emit_user_event(
            "L1-02:dod_modified",
            {
                "wp_id": "wp-2",
                "dod_old": "lint+typecheck",
                "dod_new": "lint+typecheck+e2e",
                "ui_session_id": "ui-2",
            },
            user_id="user-bob",
        )

        gwt.then("audit 含 old/new DoD + user_id")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-02:dod_modified",
            payload_contains={"wp_id": "wp-2", "user_id": "user-bob"},
        )
        assert len(events) == 1
        assert events[0]["payload"]["dod_old"] == "lint+typecheck"
        assert events[0]["payload"]["dod_new"] == "lint+typecheck+e2e"


def test_t3_skip_wp_with_user_authorization(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T3 · user 显式授权跳过 WP · audit 含 skip_wp + authorization."""
    with gwt("T3 · 跳过 WP user 授权"):
        gwt.given("wp-3 尚未完成 · user 决定跳过")

        gwt.when("user emit IC-19 skip_wp · explicit authorization")
        emit_user_event(
            "L1-03:wp_skipped",
            {
                "wp_id": "wp-3",
                "reason": "out of scope",
                "explicit_authorization": True,
            },
            user_id="user-charlie",
        )

        gwt.then("audit 含 skip + explicit_authorization=True + user_id")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_skipped",
            payload_contains={
                "wp_id": "wp-3",
                "explicit_authorization": True,
                "user_id": "user-charlie",
            },
        )
        assert len(events) == 1


def test_t4_force_block_via_ui(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_user_event,
    gwt: GWT,
) -> None:
    """T4 · user 强制 BLOCK · halt project · audit 含 force_block."""
    with gwt("T4 · 强制 BLOCK 干预"):
        gwt.given("project 跑中 · user 决定强制阻塞")

        gwt.when("user emit IC-19 force_block")
        emit_user_event(
            "L1-01:user_intervention",
            {
                "action": "force_block",
                "reason": "manual halt for investigation",
                "block_id": "block-t4-1",
            },
            user_id="user-david",
        )

        gwt.then("audit 含 force_block + user_id + block_id")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:user_intervention",
            payload_contains={
                "action": "force_block",
                "block_id": "block-t4-1",
                "user_id": "user-david",
            },
        )
        assert len(events) == 1
