"""SLO-07 · ic_14_verdict_p99 ≤ 50ms · Gate verdict emit.

阈值: 50ms (IC-14 §SLO)
来源: orchestrate_s5 全链 · trace adapt → IC-20 dispatch → wait → 双签 → DoD verdict → result

度量定义:
- orchestrate_s5(trace, deps) async 调 wall ms · 走完 7 步流水
- 实测 mock 路径 P99 ≈ 0.08ms · 50ms 阈值含 600x 余量

6 TC:
- T1 baseline · 1000 次 PASS · P99 ≤ 50ms
- T2 cold start · 首 50 次 P99 ≤ 50ms
- T3 持续 5 个滑窗
- T4 降级 · FAIL_L4 timeout 路径 · P99 ≤ 50ms (异常路径)
- T5 retry path · 第 1 次 fail + 第 2 次 success · P99 ≤ 50ms
- T6 退化告警 · 75ms 样本必触发
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.quality_loop.verifier.orchestrator import VerifierDeps, orchestrate_s5
from app.quality_loop.verifier.schemas import IC20DispatchResult, VerifierVerdict
from app.quality_loop.verifier.trace_adapter import MockExecutionTrace
from tests.shared.perf_helpers import LatencySample, assert_p99_under

SLO_BUDGET_MS = 50.0


class CtrlDelegator:
    """简化版 delegator · 默认 dispatched=True."""

    def __init__(self, queue: list[Any] | None = None) -> None:
        self.queue = list(queue or [])
        self.calls: list[Any] = []

    async def delegate_verifier(self, command):
        self.calls.append(command)
        idx = len(self.calls) - 1
        if idx < len(self.queue):
            b = self.queue[idx]
            if isinstance(b, Exception):
                raise b
            return b
        return IC20DispatchResult(
            delegation_id=command.delegation_id,
            dispatched=True,
            verifier_session_id="sub-default",
        )


class CtrlWaiter:
    """简化版 waiter · 注入 output 或 exc."""

    def __init__(self, output: dict | None = None, exc: Exception | None = None) -> None:
        self.output = output
        self.exc = exc

    async def wait(self, *, delegation_id, verifier_session_id, timeout_s):
        if self.exc is not None:
            raise self.exc
        return self.output or {}


async def _no_sleep(_: float) -> None:
    return None


def _make_trace(pid: str = "proj-slo07") -> MockExecutionTrace:
    return MockExecutionTrace(
        project_id=pid,
        wp_id="wp-perf-1",
        git_head="abc123def4",
        blueprint_slice={"dod_expression": "tests_pass", "red_tests": ["r1"]},
        main_session_id="main-perf",
        ts="2026-04-24T10:00:00Z",
        artifact_refs=("app/feature.py",),
        test_report={"passed": 10, "failed": 0, "coverage": 0.85},
        acceptance_criteria={"coverage_gate": 0.8},
    )


def _out_pass() -> dict[str, Any]:
    return {
        "blueprint_alignment": {"dod_expression": "tests_pass", "red_tests": ["r1"]},
        "s4_diff_analysis": {"passed": 10, "failed": 0, "coverage": 0.85},
        "dod_evaluation": {"verdict": "PASS", "all_pass": True},
        "verifier_report_id": "vr-perf-001",
    }


@pytest.mark.perf
class TestSLO07IC14Verdict:
    """SLO-07: ic_14_verdict_p99 ≤ 50ms · 6 TC."""

    def test_t1_baseline_p99_under_50ms(self) -> None:
        """T1 · 1000 次 orchestrate_s5 · P99 ≤ 50ms · 含 50 次 warmup."""

        async def run() -> list[LatencySample]:
            # warmup
            for _ in range(50):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                await orchestrate_s5(_make_trace(), deps)
            samples: list[LatencySample] = []
            for _ in range(1000):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                t0 = time.perf_counter()
                result = await orchestrate_s5(_make_trace(), deps)
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
                assert result.verdict == VerifierVerdict.PASS
            return samples

        samples = asyncio.run(run())
        stats = assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic14_baseline")
        assert stats.p50 < 5.0, f"ic14 verdict P50 {stats.p50:.3f}ms 异常"

    def test_t2_cold_start_p99_under_50ms(self) -> None:
        """T2 · 冷启动首 50 次 · 不放宽."""

        async def run() -> list[LatencySample]:
            samples: list[LatencySample] = []
            for _ in range(50):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                t0 = time.perf_counter()
                await orchestrate_s5(_make_trace(), deps)
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic14_cold")

    def test_t3_sustained_5_windows(self) -> None:
        """T3 · 持续 5000 次 · 5 个滑窗 P99 全 ≤ 50ms."""

        async def run() -> list[float]:
            for _ in range(50):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                await orchestrate_s5(_make_trace(), deps)
            ms_list: list[float] = []
            for _ in range(5000):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                t0 = time.perf_counter()
                await orchestrate_s5(_make_trace(), deps)
                ms_list.append((time.perf_counter() - t0) * 1000.0)
            return ms_list

        ms_list = asyncio.run(run())
        for window_idx in range(5):
            window = ms_list[window_idx * 1000 : (window_idx + 1) * 1000]
            samples = [LatencySample(elapsed_ms=v) for v in window]
            assert_p99_under(
                samples, budget_ms=SLO_BUDGET_MS,
                metric_name=f"ic14_window_{window_idx}",
            )

    def test_t4_timeout_fail_l4_path_p99_under_50ms(self) -> None:
        """T4 · 降级路径 · waiter timeout → FAIL_L4 · P99 ≤ 50ms.

        异常路径性能也要在 SLO 内 (orchestrate 不能因 timeout 处理变慢).
        """

        async def run() -> list[LatencySample]:
            for _ in range(20):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(exc=TimeoutError("verifier timeout")),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                await orchestrate_s5(_make_trace(), deps)
            samples: list[LatencySample] = []
            for _ in range(500):
                deps = VerifierDeps(
                    delegator=CtrlDelegator(),
                    callback_waiter=CtrlWaiter(exc=TimeoutError("verifier timeout")),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                t0 = time.perf_counter()
                result = await orchestrate_s5(_make_trace(), deps)
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
                assert result.verdict == VerifierVerdict.FAIL_L4
            return samples

        samples = asyncio.run(run())
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic14_timeout_path")

    def test_t5_retry_path_p99_under_50ms(self) -> None:
        """T5 · 重试路径 · IC-20 第 1 次 dispatched=False · 第 2 次 success · P99 ≤ 50ms."""

        async def run() -> list[LatencySample]:
            samples: list[LatencySample] = []
            for i in range(100):
                delegator = CtrlDelegator(queue=[
                    IC20DispatchResult(
                        delegation_id=f"ver-retry-{i}",
                        dispatched=False,
                        verifier_session_id=None,
                    ),
                    IC20DispatchResult(
                        delegation_id=f"ver-retry-{i}",
                        dispatched=True,
                        verifier_session_id=f"sub-retry-{i}",
                    ),
                ])
                deps = VerifierDeps(
                    delegator=delegator,
                    callback_waiter=CtrlWaiter(_out_pass()),
                    audit_emitter=None,
                    sleep=_no_sleep,
                )
                t0 = time.perf_counter()
                await orchestrate_s5(_make_trace(), deps)
                samples.append(LatencySample(elapsed_ms=(time.perf_counter() - t0) * 1000.0))
            return samples

        samples = asyncio.run(run())
        assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic14_retry")

    def test_t6_degradation_detection(self) -> None:
        """T6 · 退化告警 · 75ms 样本必触发."""
        samples = [LatencySample(elapsed_ms=75.0) for _ in range(100)]
        with pytest.raises(AssertionError, match="SLO p99 超标"):
            assert_p99_under(samples, budget_ms=SLO_BUDGET_MS, metric_name="ic14_degraded")
        boundary = [LatencySample(elapsed_ms=49.0) for _ in range(100)]
        stats = assert_p99_under(
            boundary, budget_ms=SLO_BUDGET_MS, metric_name="ic14_boundary",
        )
        assert stats.p99 == 49.0
