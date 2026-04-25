"""SLO-01 · tick_drift_p99 ≤ 5ms · tick 调度抖动.

阈值: 5ms (work order · 比 TICK_DRIFT_SLO_MS=100ms 严)
来源: scope §11 + main-2 WP04 实测 (tick_once wall ms P99 ≈ 0.05ms)

度量定义:
- 每次 tick_once() 的 wall-clock 处理时间 (perf_counter 精度)
- 不依赖 deadline_tracker 的 drift_ms (整数 ms · 太粗)
- 5ms 上限 = 至少 100x 余量 (实测 P99 < 0.1ms)

6 TC:
- T1 baseline · 1000 次采样 P99 ≤ 5ms
- T2 cold start · 首次 50 次 P99 ≤ 5ms (无 warmup 放宽)
- T3 持续 1 分钟稳定 · 5 个 12s 滑动窗 P99 都达标
- T4 降级路径 · halt 状态下 tick_once 仍 ≤ 5ms (HALTED 拒 dispatch · loop 仍跑)
- T5 并发负载 · 10 个 scheduler 同时 tick_once 各 100 次 · P99 ≤ 5ms
- T6 退化告警 · 注入 sleep 0.01s · 测试断言能正确识别 (反向验证 assert_p99_under)
"""
from __future__ import annotations

import asyncio
import time

import pytest

from app.main_loop.tick_scheduler import TickScheduler
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
)
from tests.shared.perf_helpers import (
    LatencySample,
    LatencyStats,
    assert_p99_under,
)

SLO_BUDGET_MS = 5.0


def _build_scheduler(pid: str = "pid-slo01") -> TickScheduler:
    return TickScheduler.create_default(
        project_id=pid,
        interval_ms=100,
        decision_engine=StubDecisionEngine(
            action={"kind": "no_op"}, latency_ms=0,
        ),
        action_dispatcher=StubActionDispatcher(latency_ms=0),
    )


@pytest.mark.perf
class TestSLO01TickDrift:
    """SLO-01: tick_drift_p99 ≤ 5ms · 6 TC."""

    def test_t1_baseline_p99_under_5ms(self) -> None:
        """T1 · 1000 次采样 baseline · P99 ≤ 5ms (含 50 次 warmup)."""

        async def run() -> list[LatencySample]:
            sched = _build_scheduler()
            for _ in range(50):
                await sched.tick_once()  # warmup
            samples: list[LatencySample] = []
            for _ in range(1000):
                t0 = time.perf_counter()
                await sched.tick_once()
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="tick_drift_baseline")
        # 健康度: P50 也应 << 1ms
        assert stats.p50 < 1.0, f"tick P50 {stats.p50:.3f}ms 异常高 · loop 有性能问题"

    def test_t2_cold_start_p99_under_5ms(self) -> None:
        """T2 · 冷启动首 50 次 · 不放宽 SLO · P99 仍 ≤ 5ms."""

        async def run() -> list[LatencySample]:
            sched = _build_scheduler(pid="pid-slo01-cold")
            samples: list[LatencySample] = []
            for _ in range(50):  # 无 warmup · 直接采样
                t0 = time.perf_counter()
                await sched.tick_once()
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        # 冷启动首次可能稍慢但 P99 必须达标
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="tick_drift_cold")

    def test_t3_sustained_60s_sliding_window_p99(self) -> None:
        """T3 · 持续负载 (5000 次模拟 1 分钟) · 5 个滑窗 P99 都 ≤ 5ms.

        说明: 真跑 1 分钟会拖慢 CI · 用 5000 次 tick_once 模拟稳态.
        每窗 1000 次 · 5 个不重叠窗口都达标 = 系统持续稳定无退化.
        """

        async def run() -> list[float]:
            sched = _build_scheduler(pid="pid-slo01-sus")
            for _ in range(50):
                await sched.tick_once()  # warmup
            all_ms: list[float] = []
            for _ in range(5000):
                t0 = time.perf_counter()
                await sched.tick_once()
                all_ms.append((time.perf_counter() - t0) * 1000.0)
            return all_ms

        all_ms = asyncio.run(run())
        # 5 个滑窗 · 每窗 1000 个采样
        for window_idx in range(5):
            window = all_ms[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"tick_drift_window_{window_idx}",
            )

    def test_t4_halted_path_p99_under_5ms(self) -> None:
        """T4 · 降级路径 · HALTED 状态 · tick_once 仍跑 (拒 dispatch) · P99 ≤ 5ms.

        HALTED 状态下 loop 不退出 · halt_enforcer 拒所有 action · tick 头部 O(1) 判定 · 应更快.
        """

        async def run() -> list[LatencySample]:
            sched = _build_scheduler(pid="pid-slo01-halt")
            for _ in range(50):
                await sched.tick_once()
            # 触发 halt
            await sched.halt_enforcer.halt(halt_id="halt-slo01-t4", red_line_id="HRL-05")
            samples: list[LatencySample] = []
            for _ in range(500):
                t0 = time.perf_counter()
                await sched.tick_once()
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        # HALTED 路径不调 decision engine · 应更快
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="tick_drift_halted")

    def test_t5_concurrent_10_schedulers_p99(self) -> None:
        """T5 · 并发 10 个 scheduler 各 100 次 tick_once · P99 ≤ 5ms.

        asyncio.gather 并发 · 测 GIL/调度器自身竞争压力下 P99 是否退化.
        """

        async def one_run(idx: int) -> list[float]:
            sched = _build_scheduler(pid=f"pid-slo01-c{idx}")
            for _ in range(20):
                await sched.tick_once()
            ms_list: list[float] = []
            for _ in range(100):
                t0 = time.perf_counter()
                await sched.tick_once()
                ms_list.append((time.perf_counter() - t0) * 1000.0)
            return ms_list

        async def run_all() -> list[list[float]]:
            return await asyncio.gather(*[one_run(i) for i in range(10)])

        results = asyncio.run(run_all())
        # 汇总 1000 个采样
        all_ms = [v for sub in results for v in sub]
        samples = [LatencySample(elapsed_ms=v) for v in all_ms]
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="tick_drift_concurrent")

    def test_t6_degradation_detection_works(self) -> None:
        """T6 · 退化告警自检 · 注入 sleep 强 P99 退化 · assert_p99_under 应正确识别.

        反向 TC: 验证 perf_helpers 工具自身无 silent-pass · 防 SLO 测试集体哑铃.
        """
        # 注入 10ms sleep · 必然超 5ms SLO
        samples = [LatencySample(elapsed_ms=10.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="degraded")
        # 反向: 1ms 应通过
        clean_samples = [LatencySample(elapsed_ms=1.0) for _ in range(100)]
        stats = assert_p99_under(
            clean_samples, budget_ms=SLO_BUDGET_MS, metric_name="clean",
        )
        assert stats.p99 == 1.0
