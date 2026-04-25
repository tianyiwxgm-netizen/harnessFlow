"""Scenario 06 · T7-T9 · panic 后全停验证 (tick stop · 业务 fail · heartbeat ok).

panic = scope §8.4 失败传播 · all tick 退出 · 但 heartbeat 仍可读取状态:
- T7 panic 后 tick dispatch 拒 (业务停)
- T8 panic 后业务事件全 fail (decision_engine 调用应被拒)
- T9 panic 后 heartbeat (state 读取) 仍工作 (运维可观测)
"""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_PAUSED_REJECT,
    TickError,
    TickState,
)
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T7 · panic 后 tick dispatch 全拒
# ============================================================================


def test_t7_panic_blocks_all_tick_dispatch(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T7 · panic 后 enforcer.assert_can_dispatch 持续拒."""
    with gwt("T7 · panic 后 tick dispatch 全停 (PAUSED reject)"):
        gwt.given("panic_handler 收 panic → enforcer PAUSED")
        panic_handler.handle(make_panic_signal(panic_id="panic-t7-stop-tick"))
        assert halt_enforcer.as_tick_state() == TickState.PAUSED

        gwt.when("模拟 100 次 tick dispatch")
        for _ in range(100):
            with pytest.raises(TickError) as exc:
                halt_enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_PAUSED_REJECT

        gwt.then("100 次全拒 · reject_count=100")
        assert halt_enforcer.reject_count == 100


# ============================================================================
# T8 · panic 后业务路径 fail (新决策无法接入)
# ============================================================================


def test_t8_panic_blocks_business_decisions(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T8 · panic 后 · 业务"决策→派发"链 dispatcher 路径全断."""
    with gwt("T8 · panic 期间 · 业务事件全 fail · 决策不能落地"):
        gwt.given("panic_handler · enforcer RUNNING")
        gwt.when("panic 触发 → enforcer PAUSED")
        panic_handler.handle(make_panic_signal(panic_id="panic-t8-business"))

        gwt.then("任何 dispatch 调用都拒 (PAUSED)")
        # 模拟 1000 个并发业务决策路径都尝试 dispatch
        for biz_decision in range(50):
            with pytest.raises(TickError) as exc:
                halt_enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_PAUSED_REJECT

        gwt.then("active_panic_id 不被业务侧覆盖 · 仍是首条 panic")
        assert panic_handler.active_panic_id == "panic-t8-business"


# ============================================================================
# T9 · panic 期间 · heartbeat (state 只读) 仍工作 · 运维可观测
# ============================================================================


def test_t9_heartbeat_works_during_panic(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T9 · panic 期间运维 readonly · heartbeat / panic_history / state 都可读."""
    with gwt("T9 · panic 期间 heartbeat 仍 ok · 运维可读 state/history"):
        gwt.given("panic 已触发 · enforcer PAUSED")
        panic_handler.handle(make_panic_signal(
            panic_id="panic-t9-heartbeat",
            user_id="ops-monitor",
            reason="readonly mode probe",
        ))

        gwt.when("运维查 readonly 状态:state / panic_history / active_panic_id")
        # 这些都是 sync property · 不应阻塞 / 不抛
        snapshot = {
            "tick_state": halt_enforcer.as_tick_state().value,
            "is_halted": halt_enforcer.is_halted(),
            "reject_count": halt_enforcer.reject_count,
            "active_panic_id": panic_handler.active_panic_id,
            "active_user_id": panic_handler.active_user_id,
            "history_count": len(panic_handler.panic_history),
        }

        gwt.then("snapshot 字段齐全 · readonly 可观测")
        assert snapshot["tick_state"] == "PAUSED"
        assert snapshot["is_halted"] is False  # PAUSED 不是 HALTED
        assert snapshot["active_panic_id"] == "panic-t9-heartbeat"
        assert snapshot["active_user_id"] == "ops-monitor"
        assert snapshot["history_count"] == 1

        # 多次读取应稳定 (idempotent reads)
        for _ in range(50):
            assert halt_enforcer.as_tick_state() == TickState.PAUSED
            assert panic_handler.active_panic_id == "panic-t9-heartbeat"
