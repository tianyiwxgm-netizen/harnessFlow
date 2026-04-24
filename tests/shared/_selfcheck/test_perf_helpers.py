"""Smoke: perf_helpers 测量 + 分位数 + SLO 断言."""
from __future__ import annotations

import asyncio

import pytest

from tests.shared.perf_helpers import (
    LatencySample,
    LatencyStats,
    assert_p95_under,
    assert_p99_under,
    collect_n,
    measure_async,
)


@pytest.mark.asyncio
async def test_measure_async_captures_elapsed() -> None:
    async def _op() -> str:
        await asyncio.sleep(0.01)  # 10 ms
        return "done"

    sample = await measure_async(_op())
    assert sample.payload == "done"
    assert 5 < sample.elapsed_ms < 200  # allow CI 慢一点


@pytest.mark.asyncio
async def test_collect_n_returns_n_samples() -> None:
    async def _quick() -> int:
        return 1

    samples = await collect_n(5, lambda: _quick())
    assert len(samples) == 5
    assert all(s.payload == 1 for s in samples)


def test_latency_stats_compute_percentiles() -> None:
    samples = [LatencySample(elapsed_ms=float(v)) for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]]
    stats = LatencyStats.compute(samples)
    assert stats.count == 10
    assert stats.min == 10
    assert stats.max == 100
    # nearest-rank p99 for n=10 · k = round(0.99*9) = 9 → idx 9 → 100
    assert stats.p99 == 100


def test_latency_stats_empty_raises() -> None:
    with pytest.raises(ValueError, match="空"):
        LatencyStats.compute([])


def test_assert_p99_under_ok() -> None:
    samples = [LatencySample(elapsed_ms=v) for v in [10, 20, 30, 40, 50]]
    stats = assert_p99_under(samples, budget_ms=100.0, metric_name="tick_drift")
    assert stats.p99 <= 100


def test_assert_p99_under_fails() -> None:
    samples = [LatencySample(elapsed_ms=v) for v in [10, 20, 30, 200, 500]]
    with pytest.raises(AssertionError, match="p99 超标"):
        assert_p99_under(samples, budget_ms=100.0, metric_name="tick_drift")


def test_assert_p95_under_ok() -> None:
    samples = [LatencySample(elapsed_ms=float(v)) for v in range(1, 101)]
    # p95 for n=100 · k = round(0.95*99) = 94 → vals[94] = 95
    stats = assert_p95_under(samples, budget_ms=100.0, metric_name="kb_read")
    assert stats.p95 <= 100
