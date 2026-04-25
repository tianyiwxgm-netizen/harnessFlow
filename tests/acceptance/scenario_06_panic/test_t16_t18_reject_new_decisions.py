"""Scenario 06 · T16-T18 · panic 期间拒收新决策 (IC-01/02/03/14 都拒).

panic 期间 · scope §8.4 失败传播 · 整个决策链全断:
- T16 IC-01 state_transition · 不接收 (state_machine 应跳过)
- T17 IC-02/03 决策事件 · dispatch 拒
- T18 IC-14 rollback push · 也拒 (PAUSED reject)
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import BusHalted, Event
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_PAUSED_REJECT,
    TickError,
    TickState,
)
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T16 · panic 期间 · IC-01 state_transition 不应接收 (业务路径 dispatch 拒)
# ============================================================================


def test_t16_panic_blocks_ic01_state_transition_dispatch(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T16 · panic 后 · 试图触发 IC-01 dispatch 路径 · 全部 PAUSED reject."""
    with gwt("T16 · panic 期间 IC-01 state_transition dispatch 拒"):
        gwt.given("panic 触发 PAUSED")
        panic_handler.handle(make_panic_signal(panic_id="panic-t16-block-ic01"))
        assert halt_enforcer.as_tick_state() == TickState.PAUSED

        gwt.when("模拟 IC-01 dispatch 路径(state_machine 试 push state_transition)")
        # IC-01 实际触发会经 enforcer.assert_can_dispatch
        # PAUSED 时 assert_can_dispatch 抛 E_TICK_PAUSED_REJECT
        for ic01_attempt in range(20):
            with pytest.raises(TickError) as exc:
                halt_enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_PAUSED_REJECT

        gwt.then("20 次 IC-01 尝试全拒 · reject_count=20")
        assert halt_enforcer.reject_count == 20


# ============================================================================
# T17 · panic 期间 · IC-02/03 决策事件 dispatch 拒 (decision_engine 路径)
# ============================================================================


def test_t17_panic_blocks_ic02_ic03_decision_dispatch(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T17 · panic 后 · IC-02 decision_decided + IC-03 决策事件 dispatch 都拒.

    场景:多 IC 类型决策事件并发 · 都被 PAUSED 拦.
    """
    with gwt("T17 · panic 期间 IC-02/03 决策 dispatch 拒"):
        gwt.given("panic PAUSED 后 · 模拟多种 IC 决策事件涌入")
        panic_handler.handle(make_panic_signal(panic_id="panic-t17-multi-ic"))

        gwt.when("混合模拟 IC-02/IC-03 各 30 次 dispatch")
        # 实际 IC 路径都通过 enforcer 守门 · 模拟 60 次混合调
        for i in range(60):
            ic_type = "IC-02" if i % 2 == 0 else "IC-03"
            with pytest.raises(TickError) as exc:
                halt_enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_PAUSED_REJECT, f"{ic_type} 应被拒"

        gwt.then("60 次混合决策全拒 · 状态稳 PAUSED")
        assert halt_enforcer.reject_count == 60
        assert halt_enforcer.as_tick_state() == TickState.PAUSED


# ============================================================================
# T18 · panic 期间 · IC-14 rollback push (audit append) · BusHalted
# ============================================================================


def test_t18_panic_blocks_ic14_audit_append(
    tmp_path: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T18 · panic mark 后 · 任何 IC-14 rollback audit append 都抛 BusHalted."""
    with gwt("T18 · panic 期间 IC-14 audit append 拒 (BusHalted)"):
        gwt.given("EventBus + panic marker 已落 (模拟 panic readonly 模式)")
        bus_root = tmp_path / "ic14_blocked_bus"
        bus_root.mkdir(parents=True)
        bus = EventBus(bus_root)
        bus.halt_guard.mark_halt(
            reason="t18 panic block ic14", source="t18",
        )
        assert bus.state.value == "HALTED"

        gwt.when("试 append IC-14 rollback push 类型事件")
        bus_pid = project_id.replace("pid-", "p-")
        evt = Event(
            project_id=bus_pid,
            type="L1-04:rollback_pushed",
            actor="verifier",
            timestamp=datetime.now(UTC),
            payload={
                "route_id": "route-t18-rollback",
                "wp_id": "wp-t18",
                "verdict": "FAIL_L1",
            },
        )

        gwt.then("append 抛 BusHalted · IC-14 不能落地")
        with pytest.raises(BusHalted):
            bus.append(evt)

        gwt.when("再试 IC-04 verifier_report_issued 也拒")
        evt2 = Event(
            project_id=bus_pid,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            timestamp=datetime.now(UTC),
            payload={"verifier_report_id": "vr-t18", "verdict": "PASS"},
        )
        with pytest.raises(BusHalted):
            bus.append(evt2)

        gwt.then("所有跨 IC 写入都被 BusHalted 统一拦 · scope §8.4 失败传播")
