"""IC-17 panic 负向 / PM-14 / HALTED · 4 TC.

覆盖:
- TC-1 · 跨 pid panic 拒(E_TICK_CROSS_PROJECT)
- TC-2 · panic_id pattern 不匹配 schema 拒
- TC-3 · user_id 缺失 schema 拒
- TC-4 · 已 HALTED 期间 panic · 不降级 · history 仍记录
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_CROSS_PROJECT,
    TickError,
    TickState,
)
from app.supervisor.event_sender.schemas import HardHaltState


def test_cross_project_panic_rejected(
    panic_handler: PanicHandler,
    make_panic_signal,
    other_project_id: str,
) -> None:
    """signal.project_id != bound · E_TICK_CROSS_PROJECT."""
    bad_signal = make_panic_signal(
        panic_id="panic-cross-pid",
        pid_override=other_project_id,
    )
    with pytest.raises(TickError) as exc:
        panic_handler.handle(bad_signal)
    assert exc.value.error_code == E_TICK_CROSS_PROJECT


def test_panic_id_pattern_violation() -> None:
    """panic_id 不符 ^panic-[A-Za-z0-9_-]{3,}$ · pydantic 拒."""
    with pytest.raises(ValidationError):
        PanicSignal(
            panic_id="bad-format-no-prefix",
            project_id="pid-ic17-default",
            user_id="user-x",
            ts="2026-04-24T00:00:00Z",
        )


def test_user_id_required_schema() -> None:
    """user_id 必填 · 空字符 pydantic min_length=1 拒."""
    with pytest.raises(ValidationError):
        PanicSignal(
            panic_id="panic-no-user",
            project_id="pid-ic17-default",
            user_id="",
            ts="2026-04-24T00:00:00Z",
        )


def test_halted_state_silent_panic_record(
    halt_enforcer: HaltEnforcer,
    panic_handler: PanicHandler,
    make_panic_signal,
) -> None:
    """已 HALTED · panic 不降级 · 但 history 仍记录(was_halted=True)."""
    # 强行进入 HALTED 状态(模拟 IC-15 路径已 halt)
    halt_enforcer._state = HardHaltState.HALTED
    halt_enforcer._active_halt_id = "halt-from-ic15"

    signal = make_panic_signal(
        panic_id="panic-during-halted",
        user_id="system",
        reason="user panic during HALTED",
    )

    # PAUSED 检查不为 PAUSED · 直接 mark_panic · halted 仍是 halted(mark_panic 短路)
    # 调用 handle 会到 mark_panic · mark_panic 检测 HALTED → return 不变
    # 但 panic_handler 仍记录 history(was_halted 标记)
    result = panic_handler.handle(signal)

    # state 仍 HALTED(不被降级)
    assert halt_enforcer.as_tick_state() == TickState.HALTED
    # history 记录 was_halted=True
    h = panic_handler.panic_history
    assert len(h) == 1
    assert h[0]["was_halted"] is True
