"""L2-03 · pytest-benchmark · P99 ≤ 500ms 硬约束。

Brief §4 明文：
> 性能 SLA：L2-03 总判定 P99 ≤ 500ms（pytest-benchmark 验证 · 违反视为 BLOCK）

本 bench 测 RedLineDetector.scan() · 空 context 下的延迟（5 detector 并发）。
"""
from __future__ import annotations

import asyncio

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.red_line import RedLineDetector


def test_redline_scan_p99_under_500ms_2k_samples(benchmark) -> None:
    """RedLineDetector.scan P99 ≤ 500ms · 2k 样本 pytest-benchmark。"""
    # 每次调用构造 fresh event_loop（避免旧 loop 污染）
    # 用同一套组件（scan 是无状态的 · event_bus/halt_target 不影响 latency）
    bus = EventBusStub()
    target = MockHardHaltTarget()
    halt_req = HaltRequester(
        session_pid="proj-bench",
        target=target,
        event_bus=bus,
    )
    detector = RedLineDetector(
        session_pid="proj-bench",
        halt_requester=halt_req,
        event_bus=bus,
    )
    context: dict = {}

    def _run_once() -> int:
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(detector.scan("proj-bench", context))
            return report.total_latency_us
        finally:
            loop.close()

    # pytest-benchmark 默认多次采样 · rounds=iteration 参数微调
    benchmark.pedantic(_run_once, rounds=2000, iterations=1)

    # 验证 P99 ≤ 500ms = 500_000us = 0.5s
    # benchmark.stats 是 pytest-benchmark 内部 statistics · 访问 mean/median/stddev
    if benchmark.stats is None:
        # --benchmark-disable · 跳过 SLO 断言
        return
    stats = benchmark.stats.stats
    # stats.max 是最大值（ms 单位 · pytest-benchmark 5.x 默认 seconds）
    # 我们要的 P99 需要从 raw data 推 · 用 stats.stats.data 全集（含所有 rounds）
    # 简化：用 max 上界检查（更严格）· max < 500ms 则 P99 也 < 500ms
    max_s = stats.max
    assert max_s < 0.5, (
        f"L2-03 SLO 500ms VIOLATION: max={max_s * 1000:.1f}ms (benchmark 5.x in seconds)"
    )
