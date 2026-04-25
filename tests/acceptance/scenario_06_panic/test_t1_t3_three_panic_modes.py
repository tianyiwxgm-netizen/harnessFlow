"""Scenario 06 · T1-T3 · 3 panic 触发模式 · 端到端 5 步链.

5 步链 (IC-17 panic + scope §8.4 失败传播):
    step-1 detect      L1-09 触发 panic 条件 (≤ 50ms)
    step-2 emit        IC-17 panic_signal emit (≤ 30ms)
    step-3 stop        L1-01 全停 · all tick 退出 (≤ 20ms)
    step-4 audit       panic_history 留痕 + audit 闭环
    step-5 readonly    project 进 readonly 等运维处置

总 panic latency p99 ≤ 100ms (HRL-04 release blocker).

3 模式:
- T1 M1 bus_fsync_failed   · event-bus 写失败 (disk full / fsync ENOSPC)
- T2 M2 hash_chain_broken  · hash chain 断 (prev_hash mismatch)
- T3 M3 bus_write_failed   · IC-09 落盘失败 (append_atomic 重试耗尽)
"""
from __future__ import annotations

import time

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from app.main_loop.tick_scheduler.schemas import TickState
from tests.acceptance.scenario_06_panic.conftest import (
    PANIC_MODE_M1_BUS_FSYNC,
    PANIC_MODE_M2_HASH_CHAIN,
    PANIC_MODE_M3_BUS_WRITE,
)
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_panic_within_100ms


PANIC_MODES = [
    ("M1", "panic-t1-bus-fsync", PANIC_MODE_M1_BUS_FSYNC, "event-bus 写失败"),
    ("M2", "panic-t2-hash-chain", PANIC_MODE_M2_HASH_CHAIN, "hash chain 断"),
    ("M3", "panic-t3-bus-write", PANIC_MODE_M3_BUS_WRITE, "IC-09 落盘失败"),
]


@pytest.mark.parametrize("mode,panic_id,reason,desc", PANIC_MODES)
def test_t1_t3_three_panic_modes_full_5step_chain(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
    mode: str,
    panic_id: str,
    reason: str,
    desc: str,
) -> None:
    """T1-T3 · 3 panic 模式 · 5 步链 · ≤ 100ms (HRL-04)."""
    with gwt(f"{mode} ({desc}) · 5 步链 ≤ 100ms · HRL-04"):
        gwt.given(f"PanicHandler 干净 · enforcer RUNNING · audit-ledger empty")
        assert halt_enforcer.as_tick_state() == TickState.RUNNING

        gwt.when(f"L1-09 触发 {mode} panic 条件 → emit IC-17 panic_signal")
        signal = make_panic_signal(panic_id=panic_id, reason=reason)

        # 测端到端总延时 (handler.handle 同步)
        t0 = time.monotonic()
        result = panic_handler.handle(signal)
        t1 = time.monotonic()
        elapsed_ms = (t1 - t0) * 1000

        gwt.then(f"step-2 emit / step-3 stop · L1-01 全停 ≤ 20ms")
        # PanicResult.panic_latency_ms 是 handler 内部测的 ns 精度 latency
        assert result.paused is True
        assert result.panic_id == panic_id
        assert result.scope == "tick"
        assert result.slo_violated is False, (
            f"{mode} SLO violated · panic_latency={result.panic_latency_ms}ms"
        )

        gwt.then(f"step-3 stop · enforcer 翻 PAUSED · 业务 dispatch 全停")
        assert halt_enforcer.as_tick_state() == TickState.PAUSED

        gwt.then(f"step-4 audit · panic_history 含 reason / scope / latency_ms")
        h = panic_handler.panic_history
        assert len(h) == 1
        rec = h[0]
        assert rec["panic_id"] == panic_id
        assert rec["reason"] == reason
        assert rec["scope"] == "tick"
        assert rec["was_halted"] is False
        for k in ("panic_id", "user_id", "reason", "scope", "was_halted",
                  "latency_ms", "slo_violated", "ts_ns"):
            assert k in rec, f"audit 闭环缺字段 {k}"

        gwt.then(f"总链端到端 elapsed={elapsed_ms:.2f}ms ≤ 100ms (HRL-04)")
        assert_panic_within_100ms(t0, t1, budget_ms=100.0)
