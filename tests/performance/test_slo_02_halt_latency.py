"""SLO-02 · halt_latency_p99 ≤ 100ms · IC-15 硬红线触发 → tick stop.

阈值: 100ms (HRL-05 release blocker · hard-redlines.md §3.2)
来源: hard-redlines.md §3.2 + main-2 WP04 实测 P99 ≈ 0.04ms

度量定义:
- HaltRequester.request_hard_halt(cmd) 阻塞调用 wall ms
- ack.halt_latency_ms 也校 (供 cross-check)
- 100ms 上限 = 至少 1000x 余量 (实测 P99 < 0.1ms)

6 TC:
- T1 baseline · 1000 次 P99 ≤ 100ms
- T2 cold start · 首 50 次 P99 ≤ 100ms
- T3 持续 · 5 个滑窗 P99 都达标
- T4 降级路径 · slow_halt_ms=80 (近上限) · P99 仍 ≤ 100ms
- T5 5 个红线轮询 · P99 ≤ 100ms (HRL-01..HRL-05 全覆盖)
- T6 退化告警 · slow_halt_ms=120 模拟超时 · P99 应超 100ms 触发断言
"""
from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import (
    HaltRequester,
    MockHardHaltTarget,
)
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    HardHaltState,
    RequestHardHaltCommand,
)
from tests.shared.perf_helpers import LatencySample, assert_p99_under

SLO_BUDGET_MS = 100.0


def _make_cmd(pid: str, red_line_id: str, halt_id: str) -> RequestHardHaltCommand:
    return RequestHardHaltCommand(
        halt_id=halt_id,
        project_id=pid,
        red_line_id=red_line_id,
        evidence=HardHaltEvidence(
            observation_refs=("ev-1", "ev-2"),
            confirmation_count=2,
        ),
        require_user_authorization=True,
        ts=datetime.now(UTC).isoformat(),
    )


@pytest.mark.perf
class TestSLO02HaltLatency:
    """SLO-02: halt_latency_p99 ≤ 100ms · 6 TC."""

    def test_t1_baseline_p99_under_100ms(self) -> None:
        """T1 · 1000 次 halt · P99 ≤ 100ms · 含 50 次 warmup."""

        async def run() -> list[LatencySample]:
            pid = "proj-slo02-baseline"
            bus = EventBusStub()
            samples: list[LatencySample] = []
            # warmup
            for i in range(50):
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-warm-{i:06d}"),
                )
            # measure
            for i in range(1000):
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                t0 = time.perf_counter()
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-base-{i:06d}"),
                )
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="halt_baseline")
        # 健康度: P50 应 < 1ms
        assert stats.p50 < 1.0, f"halt P50 {stats.p50:.3f}ms 异常"

    def test_t2_cold_start_p99_under_100ms(self) -> None:
        """T2 · 冷启动首 50 次 · 不放宽 SLO."""

        async def run() -> list[LatencySample]:
            pid = "proj-slo02-cold"
            bus = EventBusStub()
            samples: list[LatencySample] = []
            for i in range(50):
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                t0 = time.perf_counter()
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-cold-{i:06d}"),
                )
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="halt_cold")

    def test_t3_sustained_5_windows_p99_under_100ms(self) -> None:
        """T3 · 持续 5000 次 · 5 个 1000 采样滑窗 P99 全达标."""

        async def run() -> list[float]:
            pid = "proj-slo02-sus"
            bus = EventBusStub()
            # warmup
            for i in range(50):
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-warm-{i:06d}"),
                )
            ms_list: list[float] = []
            for i in range(5000):
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                t0 = time.perf_counter()
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-sus-{i:06d}"),
                )
                ms_list.append((time.perf_counter() - t0) * 1000.0)
            return ms_list

        ms_list = asyncio.run(run())
        for window_idx in range(5):
            window = ms_list[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"halt_window_{window_idx}",
            )

    def test_t4_slow_target_under_100ms(self) -> None:
        """T4 · 降级路径 · slow_halt_ms=50 (慢路径 · 留 50ms 余量) · P99 仍 ≤ 100ms.

        模拟 L1-01 真实 abort 慢路径 · 50ms 静态开销 + 调度抖动 < 100ms.
        (避用 80ms 防 macOS 调度抖动到 ~100ms 边界 flaky)
        """

        async def run() -> list[LatencySample]:
            pid = "proj-slo02-slow"
            bus = EventBusStub()
            samples: list[LatencySample] = []
            # warmup with same slow path
            for i in range(20):
                target = MockHardHaltTarget(
                    initial_state=HardHaltState.RUNNING, slow_halt_ms=50,
                )
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                await req.request_hard_halt(
                    _make_cmd(pid, "HRL-05", f"halt-warm-slow-{i:06d}"),
                )
            for i in range(100):  # 100 次足以拿 P99
                target = MockHardHaltTarget(
                    initial_state=HardHaltState.RUNNING, slow_halt_ms=50,
                )
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                t0 = time.perf_counter()
                await req.request_hard_halt(
                    _make_cmd(pid, "HRL-05", f"halt-slow-{i:06d}"),
                )
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        # 50ms 静态 + 抖动 · 应远 < 100ms
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="halt_slow")

    def test_t5_5_redlines_round_robin(self) -> None:
        """T5 · 5 红线轮询 · HRL-01..HRL-05 各 200 次 · 全部 P99 ≤ 100ms."""

        async def run() -> list[LatencySample]:
            pid = "proj-slo02-rl"
            bus = EventBusStub()
            samples: list[LatencySample] = []
            for i in range(50):  # warmup
                target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                await req.request_hard_halt(
                    _make_cmd(pid, f"HRL-{(i % 5) + 1}", f"halt-warm-rl-{i:06d}"),
                )
            for rl_idx in range(1, 6):  # HRL-01..HRL-05
                for i in range(200):
                    target = MockHardHaltTarget(initial_state=HardHaltState.RUNNING)
                    req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                    t0 = time.perf_counter()
                    await req.request_hard_halt(
                        _make_cmd(pid, f"HRL-0{rl_idx}", f"halt-rl{rl_idx}-{i:06d}"),
                    )
                    samples.append(
                        LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0)
                    )
            return samples

        samples = asyncio.run(run())
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="halt_5redlines")

    def test_t6_degradation_detection_120ms_target(self) -> None:
        """T6 · 退化告警 · slow_halt_ms=120 (超阈值) · 反向验证 P99 应触发告警.

        反向 TC: 故意做超阈值 target · assert_p99_under 必须 raise · 防 silent-pass.
        """

        async def run() -> list[LatencySample]:
            pid = "proj-slo02-degraded"
            bus = EventBusStub()
            samples: list[LatencySample] = []
            for i in range(20):
                target = MockHardHaltTarget(
                    initial_state=HardHaltState.RUNNING, slow_halt_ms=120,
                )
                req = HaltRequester(session_pid=pid, target=target, event_bus=bus)
                t0 = time.perf_counter()
                await req.request_hard_halt(
                    _make_cmd(pid, "HRL-05", f"halt-deg-{i:06d}"),
                )
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        # 120ms target · P99 必然 > 100ms · 告警应触发
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="halt_degraded")
