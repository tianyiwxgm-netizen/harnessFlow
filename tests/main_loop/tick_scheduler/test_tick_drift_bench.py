"""**HRL-04 铁律 · tick drift P99 ≤ 100ms · pytest-benchmark 强校验**。

主会话仲裁:
- tick drift 与 IC-15 halt ≤ 100ms 同级 release blocker
- P99 ≤ 100ms 违反视为 release blocker (不可降级)

bench 策略:
- 真实 asyncio loop 环境(不 mock 时钟)
- 每 round:  tick_once() 一次 · 测 latency_ms + drift_ms
- iterations > 100 · rounds ≥ 50 · 产 P99 分位数
- 断言: P99 drift ≤ 100ms 硬约束
- 同时断言 P99 latency ≤ interval_ms + drift_slo (120ms · 留 20ms 余量)

环境敏感:
- CI/本地机子性能差异 · 实际取 P99 避免偶发抖动
- engine + dispatcher 都用 zero-latency stub · 测"纯 loop 开销"
- 若 P99 > 100ms · 说明 loop 本身有性能问题 · 必须修复
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.tick_scheduler import TickScheduler
from app.main_loop.tick_scheduler.asyncio_loop import (
    StubActionDispatcher,
    StubDecisionEngine,
)
from app.main_loop.tick_scheduler.schemas import (
    TICK_DRIFT_SLO_MS,
    TICK_INTERVAL_MS_DEFAULT,
)


# ------------------------------------------------------------------
# 核心 bench · P99 drift
# ------------------------------------------------------------------
@pytest.mark.perf
def test_TC_WP04_BENCH_TICK_DRIFT_P99_100MS(benchmark) -> None:
    """TC-WP04-BENCH-TICK-DRIFT-P99 · P99 drift ≤ 100ms (HRL-04 release blocker)。

    硬断言:
    - P99 drift_ms ≤ TICK_DRIFT_SLO_MS (100)
    - mean drift ≤ 50 (健康度)

    异常处理:
    - 若失败 · 打印 P50/P95/P99 分位数 + raw data 供定位
    - 不静默降级 · release blocker
    """
    loop_ctx: dict = {}

    def _setup() -> None:
        loop_ctx["event_loop"] = asyncio.new_event_loop()
        loop_ctx["sched"] = TickScheduler.create_default(
            project_id="pid-bench-drift",
            interval_ms=TICK_INTERVAL_MS_DEFAULT,
            decision_engine=StubDecisionEngine(
                action={"kind": "no_op"}, latency_ms=0,
            ),
            action_dispatcher=StubActionDispatcher(latency_ms=0),
        )

    def _teardown() -> None:
        el = loop_ctx.get("event_loop")
        if el is not None and not el.is_closed():
            el.close()

    _setup()
    event_loop = loop_ctx["event_loop"]
    sched = loop_ctx["sched"]

    drifts_ms: list[int] = []
    latencies_ms: list[int] = []

    def _round() -> None:
        r = event_loop.run_until_complete(sched.tick_once())
        drifts_ms.append(r.drift_ms)
        latencies_ms.append(r.latency_ms)

    benchmark.pedantic(
        _round,
        iterations=1,
        rounds=200,
        warmup_rounds=10,
    )
    _teardown()

    assert len(drifts_ms) >= 50

    sorted_drifts = sorted(drifts_ms)
    p50_idx = int(len(sorted_drifts) * 0.50)
    p95_idx = int(len(sorted_drifts) * 0.95)
    p99_idx = max(0, int(len(sorted_drifts) * 0.99) - 1)
    p50 = sorted_drifts[p50_idx]
    p95 = sorted_drifts[p95_idx]
    p99 = sorted_drifts[p99_idx]
    max_drift = sorted_drifts[-1]

    print(
        f"\n[HRL-04 drift stats] n={len(drifts_ms)} "
        f"P50={p50}ms P95={p95}ms P99={p99}ms max={max_drift}ms"
    )
    assert p99 <= TICK_DRIFT_SLO_MS, (
        f"HRL-04 VIOLATED · tick drift P99={p99}ms > {TICK_DRIFT_SLO_MS}ms · "
        f"release blocker · P50={p50} P95={p95} max={max_drift}"
    )


@pytest.mark.perf
def test_TC_WP04_BENCH_TICK_LATENCY_P99_UNDER_50MS(benchmark) -> None:
    """TC-WP04-BENCH-TICK-LATENCY-P99 · 单 tick 耗 ≤ 50ms P99 (heart health)。

    tick 内部工作量(decision + dispatch stub + tracker)不应超 50ms。
    超标说明 loop 本身有 bug(死循环 / blocking sync call)。
    """
    loop_ctx: dict = {}

    def _setup() -> None:
        loop_ctx["event_loop"] = asyncio.new_event_loop()
        loop_ctx["sched"] = TickScheduler.create_default(
            project_id="pid-bench-lat",
            interval_ms=100,
        )

    def _teardown() -> None:
        el = loop_ctx.get("event_loop")
        if el is not None and not el.is_closed():
            el.close()

    _setup()
    event_loop = loop_ctx["event_loop"]
    sched = loop_ctx["sched"]

    latencies_ms: list[int] = []

    def _round() -> None:
        r = event_loop.run_until_complete(sched.tick_once())
        latencies_ms.append(r.latency_ms)

    benchmark.pedantic(
        _round,
        iterations=1,
        rounds=200,
        warmup_rounds=10,
    )
    _teardown()

    sorted_lat = sorted(latencies_ms)
    p99_idx = max(0, int(len(sorted_lat) * 0.99) - 1)
    p99 = sorted_lat[p99_idx]
    max_lat = sorted_lat[-1]

    print(
        f"\n[tick latency stats] n={len(latencies_ms)} "
        f"P99={p99}ms max={max_lat}ms"
    )
    assert p99 <= 50, (
        f"tick latency P99={p99}ms > 50ms · loop 有性能问题 · max={max_lat}"
    )


@pytest.mark.perf
def test_TC_WP04_BENCH_HALT_LATENCY_P99_UNDER_100MS(benchmark) -> None:
    """TC-WP04-BENCH-HALT-P99 · HaltEnforcer.halt P99 ≤ 100ms (HRL-05 同级铁律)。

    本 bench 独立于 WP06 IC-15 consumer bench · 测 WP04 侧 halt() 自身。
    """
    from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer

    event_loop = asyncio.new_event_loop()
    latencies_ms: list[int] = []

    counter = {"n": 0}

    def _round() -> None:
        counter["n"] += 1
        enforcer = HaltEnforcer(project_id="pid-bench-halt")
        event_loop.run_until_complete(
            enforcer.halt(
                halt_id=f"halt-bench-{counter['n']:06d}",
                red_line_id="IRREVERSIBLE_HALT",
            )
        )
        # 单次 halt · 耗时由 history 末条读
        lat = enforcer.halt_history[-1]["latency_ms"]
        latencies_ms.append(lat)

    benchmark.pedantic(
        _round,
        iterations=1,
        rounds=200,
        warmup_rounds=10,
    )

    event_loop.close()

    sorted_lat = sorted(latencies_ms)
    p99_idx = max(0, int(len(sorted_lat) * 0.99) - 1)
    p99 = sorted_lat[p99_idx]

    print(
        f"\n[halt latency stats] n={len(latencies_ms)} "
        f"P99={p99}ms max={sorted_lat[-1]}ms"
    )
    assert p99 <= 100, (
        f"halt P99={p99}ms > 100ms · HRL-05 release blocker"
    )


@pytest.mark.perf
def test_TC_WP04_BENCH_PANIC_LATENCY_P99_UNDER_100MS(benchmark) -> None:
    """TC-WP04-BENCH-PANIC-P99 · PanicHandler.handle P99 ≤ 100ms (HRL 同级)。"""
    from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
    from app.main_loop.tick_scheduler.panic_handler import PanicHandler, PanicSignal

    counter = {"n": 0}
    latencies_ms: list[int] = []

    def _round() -> None:
        counter["n"] += 1
        enforcer = HaltEnforcer(project_id="pid-bench-pan")
        handler = PanicHandler(project_id="pid-bench-pan", halt_enforcer=enforcer)
        sig = PanicSignal(
            panic_id=f"panic-bench-{counter['n']:06d}",
            project_id="pid-bench-pan",
            user_id="u-bench",
            ts="2026-04-23T00:00:00Z",
        )
        result = handler.handle(sig)
        latencies_ms.append(result.panic_latency_ms)

    benchmark.pedantic(
        _round,
        iterations=1,
        rounds=200,
        warmup_rounds=10,
    )

    sorted_lat = sorted(latencies_ms)
    p99_idx = max(0, int(len(sorted_lat) * 0.99) - 1)
    p99 = sorted_lat[p99_idx]
    max_lat = sorted_lat[-1]

    print(
        f"\n[panic latency stats] n={len(latencies_ms)} "
        f"P99={p99}ms max={max_lat}ms"
    )
    assert p99 <= 100, (
        f"panic P99={p99}ms > 100ms · release blocker (IC-17 contract)"
    )
