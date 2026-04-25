"""Scenario 06 · T13-T15 · 恢复路径 (运维清 panic + 重启 · audit chain 重建 · resume).

恢复链:
- T13 运维清 panic + 重启 → 新 enforcer 起 RUNNING
- T14 audit chain 在恢复后可继续 (新 append seq 接续旧 chain)
- T15 PAUSED → resume() → RUNNING · dispatch 恢复 · history 留痕

注:HALTED 是不可逆的 (硬红线) · 但 PAUSED (panic) 可被 resume 解.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.halt_guard import ADMIN_TOKEN_ENV_VAR
from app.l1_09.event_bus.schemas import Event
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from app.main_loop.tick_scheduler.schemas import TickState
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_hash_chain_intact,
    list_events,
)


# ============================================================================
# T13 · 运维清 panic 标志 + 重启 → 新 enforcer 起 RUNNING
# ============================================================================


def test_t13_recovery_after_ops_clears_panic(
    tmp_path: Path,
    monkeypatch,
    project_id: str,
    gwt: GWT,
) -> None:
    """T13 · panic → ops admin_token 清 → 重启 → enforcer RUNNING."""
    with gwt("T13 · 恢复路径 · ops clear + restart → RUNNING"):
        gwt.given("session A · panic mark + enforcer PAUSED")
        bus_root = tmp_path / "recovery_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        bus_a.halt_guard.mark_halt(reason="recovery test", source="t13")
        assert bus_a.halt_guard.is_halted() is True

        # 同时模拟 enforcer 因为 panic 进 PAUSED
        enforcer_a = HaltEnforcer(project_id=project_id)
        enforcer_a.mark_panic()
        assert enforcer_a.as_tick_state() == TickState.PAUSED

        gwt.when("运维清 marker · session A 关")
        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "recovery-token-t13")
        cleared = bus_a.halt_guard.clear_halt(admin_token="recovery-token-t13")
        assert cleared is True
        del bus_a, enforcer_a

        gwt.when("session B 重启 · 新 enforcer + 新 bus")
        bus_b = EventBus(bus_root)
        enforcer_b = HaltEnforcer(project_id=project_id)

        gwt.then("bus 不再 halted · 新 enforcer 默认 RUNNING")
        assert bus_b.halt_guard.is_halted() is False
        assert enforcer_b.as_tick_state() == TickState.RUNNING
        assert enforcer_b.is_halted() is False


# ============================================================================
# T14 · audit chain 重建 · 新 append seq 接续旧 chain
# ============================================================================


def test_t14_audit_chain_continues_after_recovery(
    tmp_path: Path,
    monkeypatch,
    project_id: str,
    gwt: GWT,
) -> None:
    """T14 · session A 写 2 events → panic → ops 清 → session B 续 append → chain 完整."""
    with gwt("T14 · audit chain 跨恢复完整 · seq 接续 · prev_hash 不断"):
        gwt.given("session A · 写 2 events 后 panic + halt marker")
        bus_root = tmp_path / "chain_recovery_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        bus_pid = project_id.replace("pid-", "p-")  # bus 端 pid

        for i in range(2):
            evt = Event(
                project_id=bus_pid,
                type="L1-01:tick_dispatched",
                actor="main_loop",
                timestamp=datetime.now(UTC),
                payload={"action": f"pre_panic_{i}"},
            )
            bus_a.append(evt)
        assert assert_ic_09_hash_chain_intact(bus_root, project_id=bus_pid) == 2

        # 触发 panic marker
        bus_a.halt_guard.mark_halt(reason="t14 chain recovery", source="t14")

        gwt.when("运维清 marker · session B 起 + append 第 3 条")
        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "chain-recovery-token-t14")
        bus_a.halt_guard.clear_halt(admin_token="chain-recovery-token-t14")
        del bus_a

        bus_b = EventBus(bus_root)
        evt3 = Event(
            project_id=bus_pid,
            type="L1-01:tick_dispatched",
            actor="main_loop",
            timestamp=datetime.now(UTC),
            payload={"action": "post_recovery"},
        )
        result3 = bus_b.append(evt3)

        gwt.then("第 3 条 seq=3 · prev_hash 串到第 2 条的 hash · chain 完整")
        assert result3.persisted is True
        assert result3.sequence == 3

        n = assert_ic_09_hash_chain_intact(bus_root, project_id=bus_pid)
        assert n == 3

        events = list_events(bus_root, bus_pid)
        assert len(events) == 3
        # 第 3 条接续第 2 条
        assert events[2]["prev_hash"] == events[1]["hash"]
        assert events[2]["sequence"] == 3
        assert events[2]["payload"]["action"] == "post_recovery"


# ============================================================================
# T15 · panic_handler.resume() · PAUSED → RUNNING · history 留痕
# ============================================================================


def test_t15_panic_handler_resume_clears_paused(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T15 · panic_handler.resume() · PAUSED → RUNNING · 历史 panic 仍 in history."""
    with gwt("T15 · panic 后 resume · 状态恢复 + history 留痕"):
        gwt.given("panic 触发 → enforcer PAUSED")
        signal = make_panic_signal(panic_id="panic-t15-resume")
        panic_handler.handle(signal)
        assert halt_enforcer.as_tick_state() == TickState.PAUSED

        gwt.when("调 panic_handler.resume() (运维或 user IC-17 authorize)")
        panic_handler.resume()

        gwt.then("enforcer state=RUNNING · dispatch 恢复 (assert_can_dispatch 不抛)")
        assert halt_enforcer.as_tick_state() == TickState.RUNNING
        halt_enforcer.assert_can_dispatch()  # 不应抛

        gwt.then("active_panic_id 清空 · 但 panic_history 留痕 (审计追溯)")
        assert panic_handler.active_panic_id is None
        assert panic_handler.active_user_id is None
        assert len(panic_handler.panic_history) == 1
        assert panic_handler.panic_history[0]["panic_id"] == "panic-t15-resume"
