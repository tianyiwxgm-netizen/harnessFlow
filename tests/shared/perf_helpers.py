"""tests/shared/perf_helpers.py · 性能测量 helper(M3-WP01).

**定位**:
    给 M3-WP07 performance-integration-tests(7 SLO) + IC-15/17 100ms 硬约束用的
    延时采样 + P99/P95/P50 统计工具库.

**为何不直接用 pytest-benchmark**:
    - pytest-benchmark 侧重微基准(纯 CPU / 同步 function)
    - 集成测试的"延时"含 async + 跨 L1 真实调用 · 更适合手工 monotonic() 采样
    - 但**IC-15/17 release blocker benchmark 仍应用 pytest-benchmark**(见 dev-α WP12)

**核心 API**:
    - measure_async(coro) → LatencySample(ms + payload)
    - collect_n(n, factory) → list[LatencySample]
    - LatencyStats.compute(samples) → {p50, p95, p99, max, count}
    - assert_p99_under(samples, budget_ms) · P99 硬红线断言

**PRD §7.1 11 条时延阈值**(示意):
    tick_drift_p99 ≤ 100ms / panic_to_paused_p99 ≤ 100ms / halt_ack_p99 ≤ 100ms /
    audit_emit_p99 ≤ 50ms / kb_read_p99 ≤ 1000ms / ...
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine


@dataclass
class LatencySample:
    """单次延时采样."""

    elapsed_ms: float
    payload: Any = None


async def measure_async(coro: Coroutine[Any, Any, Any]) -> LatencySample:
    """测量单个 coroutine 的执行延时 · monotonic 精度.

    用法:
        sample = await measure_async(harness.step())
        assert sample.elapsed_ms < 100
    """
    t0 = time.monotonic()
    payload = await coro
    elapsed = (time.monotonic() - t0) * 1000.0
    return LatencySample(elapsed_ms=elapsed, payload=payload)


async def collect_n(
    n: int,
    factory: Callable[[], Coroutine[Any, Any, Any]],
) -> list[LatencySample]:
    """连续采样 n 次 · 每次由 factory() 构造新 coroutine.

    注意: factory 必须每次返**新** coroutine(不能返共用的 · coroutine 只能 await 一次).

    用法:
        samples = await collect_n(100, lambda: harness.step())
    """
    out: list[LatencySample] = []
    for _ in range(n):
        coro = factory()
        out.append(await measure_async(coro))
    return out


@dataclass
class LatencyStats:
    """P50/P95/P99/max/count 汇总."""

    count: int
    p50: float
    p95: float
    p99: float
    max: float
    min: float

    @classmethod
    def compute(cls, samples: list[LatencySample]) -> LatencyStats:
        if not samples:
            raise ValueError("samples 为空")
        vals = sorted(s.elapsed_ms for s in samples)
        n = len(vals)

        def _percentile(p: float) -> float:
            """Nearest-rank percentile(避浮点 quantile · 稳)."""
            if n == 1:
                return vals[0]
            k = int(round(p * (n - 1)))
            return vals[max(0, min(k, n - 1))]

        return cls(
            count=n,
            p50=_percentile(0.50),
            p95=_percentile(0.95),
            p99=_percentile(0.99),
            max=vals[-1],
            min=vals[0],
        )

    def summary(self) -> str:
        return (
            f"count={self.count} min={self.min:.2f} p50={self.p50:.2f} "
            f"p95={self.p95:.2f} p99={self.p99:.2f} max={self.max:.2f} (ms)"
        )


def assert_p99_under(
    samples: list[LatencySample],
    *,
    budget_ms: float,
    metric_name: str = "latency",
) -> LatencyStats:
    """SLO 断言: P99 ≤ budget_ms.

    返: 计算好的 LatencyStats(供继续断言 min/max/p95 等).

    失败 message 含 stats summary + 超标比例.
    """
    stats = LatencyStats.compute(samples)
    if stats.p99 > budget_ms:
        exceed_pct = (stats.p99 - budget_ms) / budget_ms * 100.0
        raise AssertionError(
            f"SLO p99 超标 {metric_name}: 期望≤{budget_ms}ms 实际 p99={stats.p99:.2f}ms "
            f"(超 {exceed_pct:+.1f}%)\n"
            f"  详情: {stats.summary()}"
        )
    return stats


def assert_p95_under(
    samples: list[LatencySample],
    *,
    budget_ms: float,
    metric_name: str = "latency",
) -> LatencyStats:
    """SLO 断言: P95 ≤ budget_ms(部分 SLO 用 P95 · 如非 release blocker 指标)."""
    stats = LatencyStats.compute(samples)
    if stats.p95 > budget_ms:
        raise AssertionError(
            f"SLO p95 超标 {metric_name}: 期望≤{budget_ms}ms 实际 p95={stats.p95:.2f}ms\n"
            f"  详情: {stats.summary()}"
        )
    return stats
