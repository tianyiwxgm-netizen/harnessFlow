"""IC-17 · panic 8 TC: 触发条件 + SLO + 全停 + audit + 恢复.

3 panic 触发条件:
- TC-1 reason="bus_fsync_failed" · 事件总线写失败
- TC-2 reason="hash_chain_broken" · hash chain 断
- TC-3 reason="bus_write_failed" · IC-09 落盘失败

5 流程 TC:
- TC-4 100ms SLO · panic_latency_ms <= 100
- TC-5 L1-01 全停(enforce_can_dispatch 拒)
- TC-6 L1-09 audit 闭环(panic_history 含字段)
- TC-7 恢复路径 resume() → RUNNING
- TC-8 已 PAUSED 收 panic · 拒(ALREADY_PAUSED) · HALTED 不被降级
"""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_CROSS_PROJECT,
    E_TICK_HALTED_REJECT,
    E_TICK_PANIC_ALREADY_PAUSED,
    E_TICK_PAUSED_REJECT,
    TickError,
    TickState,
)
from app.supervisor.event_sender.schemas import HardHaltState


# ============================================================================
# 3 触发条件 panic + reason 透传
# ============================================================================


@pytest.mark.parametrize("trigger_reason,panic_id", [
    ("bus_fsync_failed: events.jsonl fsync ENOSPC", "panic-bus-fsync"),
    ("hash_chain_broken: prev_hash mismatch at seq=42", "panic-hash-broken"),
    ("bus_write_failed: append_atomic POSIX EIO", "panic-bus-write"),
])
def test_3_trigger_conditions_emit_panic(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    trigger_reason: str,
    panic_id: str,
) -> None:
    """3 触发条件 · panic 落 PAUSED · reason 透传 · history 留痕."""
    signal = make_panic_signal(
        panic_id=panic_id,
        user_id="system-supervisor",
        reason=trigger_reason,
    )

    result = panic_handler.handle(signal)

    assert result.paused is True
    assert result.panic_id == panic_id
    assert halt_enforcer.as_tick_state() == TickState.PAUSED

    # history 含 reason / latency / scope
    h = panic_handler.panic_history
    assert len(h) == 1
    assert h[0]["panic_id"] == panic_id
    assert h[0]["reason"] == trigger_reason
    assert h[0]["scope"] == "tick"


# ============================================================================
# 100ms SLO + L1-01 全停 + audit + 恢复 + 幂等
# ============================================================================


def test_panic_within_100ms_slo(
    panic_handler: PanicHandler,
    make_panic_signal,
) -> None:
    """TC-4 · panic_latency_ms ≤ 100ms (HRL-04)."""
    signal = make_panic_signal(panic_id="panic-slo-check")
    result = panic_handler.handle(signal)
    assert result.panic_latency_ms <= 100
    assert result.slo_violated is False


def test_panic_blocks_dispatch(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
) -> None:
    """TC-5 · panic 后 dispatch 被拒(L1-01 全停)."""
    panic_handler.handle(make_panic_signal(panic_id="panic-block-dispatch"))

    with pytest.raises(TickError) as exc:
        halt_enforcer.assert_can_dispatch()
    assert exc.value.error_code == E_TICK_PAUSED_REJECT
    # reject_count 累加
    assert halt_enforcer.reject_count == 1


def test_panic_audit_closure(
    panic_handler: PanicHandler,
    make_panic_signal,
) -> None:
    """TC-6 · L1-09 audit 闭环 · panic_history 含 ts_ns / latency_ms / was_halted."""
    signal = make_panic_signal(
        panic_id="panic-audit-closure",
        user_id="user-admin",
        reason="user requested panic",
    )
    panic_handler.handle(signal)

    h = panic_handler.panic_history
    assert len(h) == 1
    rec = h[0]
    # 必含字段(L1-09 audit 闭环最小集)
    for key in ("panic_id", "user_id", "reason", "scope",
                "was_halted", "latency_ms", "slo_violated", "ts_ns"):
        assert key in rec, f"audit 闭环缺字段 {key}"
    assert rec["was_halted"] is False  # 初始 RUNNING


def test_panic_resume_path(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
) -> None:
    """TC-7 · resume() · state=PAUSED → RUNNING · dispatch 恢复."""
    panic_handler.handle(make_panic_signal(panic_id="panic-resume"))
    assert halt_enforcer.as_tick_state() == TickState.PAUSED

    panic_handler.resume()
    assert halt_enforcer.as_tick_state() == TickState.RUNNING
    # active_panic 清零
    assert panic_handler.active_panic_id is None
    # dispatch 不再被拒
    halt_enforcer.assert_can_dispatch()  # 不抛


def test_already_paused_rejected(
    panic_handler: PanicHandler,
    make_panic_signal,
) -> None:
    """TC-8 · 已 PAUSED 再 panic · ALREADY_PAUSED 拒 · 幂等."""
    panic_handler.handle(make_panic_signal(panic_id="panic-first"))

    with pytest.raises(TickError) as exc:
        panic_handler.handle(make_panic_signal(panic_id="panic-second"))
    assert exc.value.error_code == E_TICK_PANIC_ALREADY_PAUSED
    # active_panic_id 仍是第一个(未被覆盖)
    assert panic_handler.active_panic_id == "panic-first"
