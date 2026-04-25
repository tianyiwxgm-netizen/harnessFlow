"""B3 · L1-09 panic → L1-01 全停 (IC-17) · 5 TC.

链路:
    user_panic 信号 → PanicHandler.handle → HaltEnforcer.mark_panic →
    L1-01 state=PAUSED · tick stop · ≤ 100ms SLO.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_CROSS_PROJECT,
    E_TICK_PANIC_ALREADY_PAUSED,
    TickError,
    TickState,
)


def _make_panic_signal(
    *,
    project_id: str,
    panic_id: str = "panic-aaa",
    user_id: str = "user-1",
    reason: str | None = None,
    scope: str = "tick",
) -> PanicSignal:
    return PanicSignal(
        panic_id=panic_id,
        project_id=project_id,
        user_id=user_id,
        reason=reason,
        ts=datetime.now(UTC).isoformat(),
        scope=scope,
    )


class TestB3PanicStopTick:
    """B3 · IC-17 panic → tick stop · 5 TC."""

    def test_b3_01_panic_pauses_tick_within_100ms(self) -> None:
        """B3.1: user_panic → PAUSED 落定 ≤ 100ms (HRL-04)."""
        pid = "pid-test01"
        enforcer = HaltEnforcer(project_id=pid)
        handler = PanicHandler(project_id=pid, halt_enforcer=enforcer)
        signal = _make_panic_signal(project_id=pid)
        # SLO 测
        start = time.monotonic()
        result = handler.handle(signal)
        end = time.monotonic()
        elapsed_ms = (end - start) * 1000.0
        assert elapsed_ms <= 100.0, f"panic 超时 {elapsed_ms:.2f}ms"
        # 状态机
        assert result.paused is True
        assert result.panic_latency_ms <= 100
        assert result.slo_violated is False
        assert enforcer.as_tick_state() == TickState.PAUSED

    def test_b3_02_action_dispatch_rejected_after_panic(self) -> None:
        """B3.2: panic 后 enforce_can_dispatch 拒 action · E_TICK_PAUSED_REJECT.

        L1-01 tick loop 收 panic 后所有 action 拒 · ≤ 0 dispatch.
        """
        from app.main_loop.tick_scheduler.schemas import E_TICK_PAUSED_REJECT

        pid = "pid-test02"
        enforcer = HaltEnforcer(project_id=pid)
        handler = PanicHandler(project_id=pid, halt_enforcer=enforcer)
        signal = _make_panic_signal(project_id=pid)
        handler.handle(signal)
        # 后续任何 action 调用都拒
        with pytest.raises(TickError) as ei:
            enforcer.assert_can_dispatch()
        assert ei.value.error_code == E_TICK_PAUSED_REJECT

    def test_b3_03_idempotent_panic_already_paused(self) -> None:
        """B3.3: 已 PAUSED 状态下再 panic · 抛 E_TICK_PANIC_ALREADY_PAUSED."""
        pid = "pid-test03"
        enforcer = HaltEnforcer(project_id=pid)
        handler = PanicHandler(project_id=pid, halt_enforcer=enforcer)
        # 首次
        handler.handle(_make_panic_signal(project_id=pid, panic_id="panic-aaa"))
        # 二次 · 抛
        with pytest.raises(TickError) as ei:
            handler.handle(_make_panic_signal(project_id=pid, panic_id="panic-bbb"))
        assert ei.value.error_code == E_TICK_PANIC_ALREADY_PAUSED

    def test_b3_04_cross_project_panic_rejected(self) -> None:
        """B3.4: 跨 pid panic · TickError E_TICK_CROSS_PROJECT.

        PM-14: PanicHandler.project_id 锁 · 跨 pid 拒.
        """
        pid_a = "pid-test04a"
        pid_b = "pid-test04b"
        enforcer = HaltEnforcer(project_id=pid_a)
        handler = PanicHandler(project_id=pid_a, halt_enforcer=enforcer)
        # B 的 panic signal · 给 A 的 handler
        signal_b = _make_panic_signal(project_id=pid_b)
        with pytest.raises(TickError) as ei:
            handler.handle(signal_b)
        assert ei.value.error_code == E_TICK_CROSS_PROJECT
        # A 的 enforcer 仍 RUNNING(未被 B 影响)
        assert enforcer.as_tick_state() == TickState.RUNNING

    def test_b3_05_resume_clears_panic_back_to_running(self) -> None:
        """B3.5: panic → resume → state=RUNNING (HRL-04 → IC-17 user_intervene authorize)."""
        pid = "pid-test05"
        enforcer = HaltEnforcer(project_id=pid)
        handler = PanicHandler(project_id=pid, halt_enforcer=enforcer)
        # panic
        handler.handle(_make_panic_signal(project_id=pid))
        assert enforcer.as_tick_state() == TickState.PAUSED
        # resume(user authorize)
        handler.resume()
        assert enforcer.as_tick_state() == TickState.RUNNING
        # 现在可以再次 panic(已不是 already_paused)
        result2 = handler.handle(_make_panic_signal(
            project_id=pid, panic_id="panic-second",
        ))
        assert result2.paused is True
