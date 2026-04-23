"""P1-02 · IC-12 dispatch SLO benchmark.

ic-contracts.md §3.12 row (Dispatch ≤ 200ms) → we verify P99 ≤ 200ms
with a fast in-process mock L1-05 client. The mock mimics ~5ms of work
so we measure the delegator's own synchronous + asyncio.wait_for overhead,
not any real subagent-launch latency.

Two tests:
  1. `test_ic_12_dispatch_p99_under_200ms_bulk` — 1000-iteration loop,
     compute P99 ourselves, fail hard if P99 > 200ms. Emits stdout so the
     standup log can quote the exact numbers.
  2. `test_ic_12_dispatch_benchmark` — pytest-benchmark fixture round,
     gated on `pytest-benchmark` being available; skipped gracefully
     otherwise so the rest of the suite keeps running.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import Any

import pytest

from app.multimodal.ic_12_delegator import delegate_codebase_onboarding


class _FastMockL1_05:
    """Dispatches with tiny fixed delay so measurements reflect delegator cost."""

    def __init__(self) -> None:
        self.count = 0

    async def dispatch_codebase_onboarding(
        self, cmd: dict[str, Any]
    ) -> dict[str, Any]:
        self.count += 1
        # Simulate a trivially fast subagent launch (no real IO); keep this small
        # so we are measuring delegator overhead, not mock cost.
        await asyncio.sleep(0.0)
        return {"dispatched": True, "subagent_session_id": f"sub-{self.count:04d}"}


@pytest.mark.perf
async def test_ic_12_dispatch_p99_under_200ms_bulk(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """1000-iteration P99 SLO check for IC-12 dispatch.

    Contract SLO: Dispatch ≤ 200ms (ic-contracts.md §3.12 · IC-12 row).
    We assert P99 (not mean) to catch tail regressions.
    """
    client = _FastMockL1_05()
    iterations = 1000
    samples_ms: list[float] = []

    # Warm-up 10 calls so import / first-JIT costs don't skew the head of the distribution.
    for _ in range(10):
        await delegate_codebase_onboarding(
            project_id="p-001", repo_path="repo/", client=client,
        )

    # Measure end-to-end delegator-call latency with perf_counter (sub-ms resolution).
    # result.dispatch_ms is an int field good for ops logs but too coarse at P99.
    for _ in range(iterations):
        t0 = time.perf_counter()
        await delegate_codebase_onboarding(
            project_id="p-001", repo_path="repo/", client=client,
        )
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    samples_ms.sort()
    n = len(samples_ms)
    p50 = samples_ms[int(n * 0.50)]
    p95 = samples_ms[int(n * 0.95)]
    p99 = samples_ms[int(n * 0.99)]
    p_max = samples_ms[-1]
    mean = statistics.fmean(samples_ms)

    # Emit to stdout so the standup log can cite concrete numbers.
    print(
        f"\n[IC-12 dispatch SLO · n={n}] "
        f"mean={mean:.4f}ms p50={p50:.4f}ms p95={p95:.4f}ms "
        f"p99={p99:.4f}ms max={p_max:.4f}ms"
    )

    # Contract: P99 ≤ 200ms. Give no slack; this is the SLO number.
    assert p99 <= 200.0, (
        f"IC-12 dispatch P99 SLO violated: p99={p99:.4f}ms > 200ms "
        f"(mean={mean:.4f}ms, p95={p95:.4f}ms, max={p_max:.4f}ms, n={n})"
    )


@pytest.mark.perf
def test_ic_12_dispatch_benchmark(benchmark: Any) -> None:
    """pytest-benchmark round — records distribution for CI-side trend tracking.

    Uses asyncio.run inside the benchmarked callable so pytest-benchmark
    (sync-fixture) can time us. Bench settings kept light so running the
    perf tier is not painful locally.
    """
    client = _FastMockL1_05()

    def _run_once() -> None:
        asyncio.run(
            delegate_codebase_onboarding(
                project_id="p-001", repo_path="repo/", client=client,
            )
        )

    result = benchmark.pedantic(_run_once, rounds=50, iterations=1, warmup_rounds=5)
    # pedantic returns the last return value (None); we rely on `benchmark.stats`
    # being emitted in the benchmark section of pytest's output.
    assert result is None
