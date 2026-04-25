"""Scenario 06 · T4-T6 · 100ms SLO 三场景 (panic_latency).

- T4 baseline       单次 panic · 干净环境 · P99 ≤ 100ms
- T5 持续负载       50 次 panic 重启循环 · P99 ≤ 100ms
- T6 冷启动         首次 PanicHandler init + 首次 panic · P99 ≤ 100ms

panic_handler.handle 是 sync · 用 time.monotonic 直接测 (不需 measure_async).
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
from tests.shared.gwt_helpers import GWT
from tests.shared.perf_helpers import LatencySample, LatencyStats, assert_p99_under


# ============================================================================
# T4 · baseline · 单次 panic
# ============================================================================


def test_t4_panic_slo_baseline_single_panic(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T4 · 单次 panic · ≤ 100ms (HRL-04)."""
    with gwt("T4 · baseline panic ≤ 100ms"):
        gwt.given("PanicHandler 干净 · enforcer RUNNING")
        gwt.when("发 1 条 panic")
        signal = make_panic_signal(panic_id="panic-t4-baseline")

        t0 = time.monotonic()
        result = panic_handler.handle(signal)
        elapsed_ms = (time.monotonic() - t0) * 1000

        gwt.then(f"端到端 elapsed_ms={elapsed_ms:.2f} ≤ 100ms")
        assert result.paused is True
        assert elapsed_ms < 100.0
        assert result.slo_violated is False


# ============================================================================
# T5 · 持续负载 · 50 次 panic 重启循环
# ============================================================================


def test_t5_panic_slo_under_load_50_panics(
    project_id: str,
    gwt: GWT,
) -> None:
    """T5 · 50 次 fresh panic_handler + handle · P99 ≤ 100ms 不退化."""
    with gwt("T5 · 50 panic 持续负载 · P99 ≤ 100ms"):
        gwt.given("循环创建 fresh enforcer + panic_handler · 模拟 50 次独立事件")
        samples: list[LatencySample] = []

        gwt.when("跑 50 次 panic + measure")
        for i in range(50):
            enforcer = HaltEnforcer(project_id=project_id)
            handler = PanicHandler(project_id=project_id, halt_enforcer=enforcer)
            signal = PanicSignal(
                panic_id=f"panic-t5-iter-{i:03d}",
                project_id=project_id,
                user_id="system-load-test",
                reason=f"load test iter={i}",
                ts=datetime.now(UTC).isoformat(),
                scope="tick",
            )
            t0 = time.monotonic()
            result = handler.handle(signal)
            elapsed_ms = (time.monotonic() - t0) * 1000
            samples.append(LatencySample(elapsed_ms=elapsed_ms, payload=result))
            assert result.paused is True

        gwt.then(f"P99 ≤ 100ms · 50 samples")
        assert len(samples) == 50
        stats = assert_p99_under(samples, budget_ms=100.0, metric_name="panic_p99")
        assert stats.max < 200.0, f"max latency 异常 stats={stats.summary()}"


# ============================================================================
# T6 · 冷启动 · PanicHandler 首次 init + 首次 panic
# ============================================================================


def test_t6_panic_slo_cold_start(
    project_id: str,
    gwt: GWT,
) -> None:
    """T6 · 全新 enforcer + handler init + 首次 panic · ≤ 100ms."""
    with gwt("T6 · 冷启动 panic ≤ 100ms"):
        gwt.given("无任何 fixture · 直接测 init+handle 整体延时")

        gwt.when("一次性 init + handle")

        def cold_start_panic() -> tuple[float, object]:
            t0 = time.monotonic()
            enforcer = HaltEnforcer(project_id=project_id)
            handler = PanicHandler(project_id=project_id, halt_enforcer=enforcer)
            signal = PanicSignal(
                panic_id="panic-t6-cold-start",
                project_id=project_id,
                user_id="system-cold",
                reason="cold start panic",
                ts=datetime.now(UTC).isoformat(),
                scope="tick",
            )
            result = handler.handle(signal)
            elapsed_ms = (time.monotonic() - t0) * 1000
            return elapsed_ms, result

        elapsed_ms, result = cold_start_panic()

        gwt.then(f"冷启动总链 elapsed={elapsed_ms:.2f}ms ≤ 100ms")
        assert result.paused is True
        assert elapsed_ms < 100.0
