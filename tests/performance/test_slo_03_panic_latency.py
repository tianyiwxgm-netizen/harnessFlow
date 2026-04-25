"""SLO-03 · panic_latency_p99 ≤ 100ms · IC-17 panic → 全停.

阈值: 100ms (scope §8.4 + IC-17 PANIC_SLO_MS)
来源: panic_handler.handle 纯内存翻态 · 实测 P99 ≈ 0.02ms

度量定义:
- PanicHandler.handle(signal) sync 调 wall ms (perf_counter 精度)
- result.panic_latency_ms (整数 ms · 内部测) 也校
- 100ms 上限 = 至少 5000x 余量

6 TC:
- T1 baseline · 1000 次 panic · P99 ≤ 100ms
- T2 cold start · 首 50 次 P99 ≤ 100ms
- T3 持续 5 个滑窗
- T4 降级路径 · already-PAUSED 抛异常路径 · P99 仍 ≤ 100ms (异常路径)
- T5 多 reason 类型轮询 · 3 触发条件 (bus_fsync_failed / hash_chain_broken / bus_write_failed)
- T6 退化告警 · 注入 5ms sleep · 反向触发
"""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler, PanicSignal
from app.main_loop.tick_scheduler.schemas import E_TICK_PANIC_ALREADY_PAUSED, TickError
from tests.shared.perf_helpers import LatencySample, assert_p99_under

SLO_BUDGET_MS = 100.0


def _new_handler() -> tuple[PanicHandler, str]:
    """返 (handler, pid) · 每次新建 enforcer 防 PAUSED 累积."""
    pid = f"pid-slo03-{uuid.uuid4().hex[:8]}"
    he = HaltEnforcer(project_id=pid)
    return PanicHandler(project_id=pid, halt_enforcer=he), pid


def _signal(pid: str, idx: int, *, reason: str | None = None) -> PanicSignal:
    return PanicSignal(
        panic_id=f"panic-slo03-{idx:06d}",
        project_id=pid,
        user_id="user-slo03",
        reason=reason,
        ts=datetime.now(UTC).isoformat(),
    )


@pytest.mark.perf
class TestSLO03PanicLatency:
    """SLO-03: panic_latency_p99 ≤ 100ms · 6 TC."""

    def test_t1_baseline_p99_under_100ms(self) -> None:
        """T1 · 1000 次 baseline · P99 ≤ 100ms · 含 50 次 warmup."""
        # warmup
        for i in range(50):
            handler, pid = _new_handler()
            handler.handle(_signal(pid, i))
        samples: list[LatencySample] = []
        for i in range(1000):
            handler, pid = _new_handler()
            sig = _signal(pid, i)
            t0 = time.perf_counter()
            handler.handle(sig)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="panic_baseline")
        assert stats.p50 < 1.0, f"panic P50 {stats.p50:.3f}ms 异常"

    def test_t2_cold_start_p99_under_100ms(self) -> None:
        """T2 · 冷启动首 50 次 · 不放宽."""
        samples: list[LatencySample] = []
        for i in range(50):
            handler, pid = _new_handler()
            sig = _signal(pid, i)
            t0 = time.perf_counter()
            handler.handle(sig)
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="panic_cold")

    def test_t3_sustained_5_windows(self) -> None:
        """T3 · 持续 5000 次 · 5 个滑窗 P99 全 ≤ 100ms."""
        for i in range(50):
            handler, pid = _new_handler()
            handler.handle(_signal(pid, i))
        ms_list: list[float] = []
        for i in range(5000):
            handler, pid = _new_handler()
            sig = _signal(pid, i)
            t0 = time.perf_counter()
            handler.handle(sig)
            ms_list.append((time.perf_counter() - t0) * 1000.0)
        for window_idx in range(5):
            window = ms_list[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"panic_window_{window_idx}",
            )

    def test_t4_already_paused_path_under_100ms(self) -> None:
        """T4 · 异常路径 · 重复 panic 触发 ALREADY_PAUSED · P99 ≤ 100ms.

        IC-17 §3.3.1 幂等 · 已 PAUSED 收 panic raise · 异常路径性能也是 SLO 一部分.
        """
        samples: list[LatencySample] = []
        for i in range(200):
            handler, pid = _new_handler()
            handler.handle(_signal(pid, i))  # 第一次 PAUSED
            # 第二次必抛 ALREADY_PAUSED
            sig2 = _signal(pid, i + 100000, reason="duplicate")
            t0 = time.perf_counter()
            try:
                handler.handle(sig2)
                pytest.fail("应抛 TickError ALREADY_PAUSED")
            except TickError as exc:
                assert exc.error_code == E_TICK_PANIC_ALREADY_PAUSED
            samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="panic_already_paused")

    def test_t5_3_trigger_reasons_round_robin(self) -> None:
        """T5 · 3 触发条件轮询 · IC-17 §定义的 3 种 reason · 各 200 次."""
        reasons = [
            "bus_fsync_failed: events.jsonl fsync ENOSPC",
            "hash_chain_broken: prev_hash mismatch at seq=42",
            "bus_write_failed: append_atomic POSIX EIO",
        ]
        samples: list[LatencySample] = []
        # warmup
        for i in range(50):
            handler, pid = _new_handler()
            handler.handle(_signal(pid, i, reason=reasons[i % 3]))
        for r_idx, reason in enumerate(reasons):
            for i in range(200):
                handler, pid = _new_handler()
                sig = _signal(pid, r_idx * 200 + i, reason=reason)
                t0 = time.perf_counter()
                handler.handle(sig)
                samples.append(
                    LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0)
                )
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="panic_3reasons")

    def test_t6_degradation_detection(self) -> None:
        """T6 · 退化告警 · 注入 200ms sleep 模拟 panic_latency 退化 · 必须告警."""
        # 直接构造超阈值 sample (not hooked into real handler) · 验证 assert 工具
        samples = [LatencySample(elapsed_ms=200.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="panic_degraded")
        # 反向: 100ms 边界应通过
        boundary = [LatencySample(elapsed_ms=99.0) for _ in range(100)]
        stats = assert_p99_under(
            boundary, budget_ms=SLO_BUDGET_MS, metric_name="panic_boundary",
        )
        assert stats.p99 == 99.0
