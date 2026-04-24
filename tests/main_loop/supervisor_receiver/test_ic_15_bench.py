"""IC-15 · **Sync ≤ 100ms HRL-05 铁律 · pytest-benchmark 硬校验**。

主会话仲裁（2026-04-23-Dev-ζ §C-2）：
- halt 端到端 ≤ 100ms 硬约束 · 不可降级
- P99 ≤ 100ms 由 pytest-benchmark 强校验 · 违反视为 release blocker

bench 策略：
- 单次 halt_target 正常路径（MockHardHaltTarget · slow_halt_ms=0）
- iterations = 100+ · 取 P99 stats.stats.data 分位数
- 断言 P99 * 1000 ≤ HALT_SLO_MS（bench 单位秒 → ms）
"""
from __future__ import annotations

import asyncio

import pytest

from app.main_loop.supervisor_receiver.ic_15_consumer import (
    HALT_SLO_MS,
    IC15Consumer,
)
from app.main_loop.supervisor_receiver.schemas import HaltSignal
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.halt_requester import MockHardHaltTarget
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)


def _make_signal(pid: str, red_line_id: str) -> HaltSignal:
    cmd = RequestHardHaltCommand(
        halt_id=f"halt-{red_line_id}-1",
        project_id=pid,
        red_line_id=red_line_id,
        evidence=HardHaltEvidence(
            observation_refs=("evt-bench-1", "evt-bench-2"),
            confirmation_count=2,
        ),
        require_user_authorization=True,
        ts="2026-04-23T00:00:00Z",
    )
    return HaltSignal.from_command(cmd, received_at_ms=0)


@pytest.mark.perf
def test_TC_WP06_IC15_BENCH_P99_100MS(benchmark) -> None:
    """TC-WP06-IC15-BENCH · P99 ≤ 100ms · HRL-05 铁律（pytest-benchmark）。

    每 round 新 consumer（避免幂等 cached 走短路径 · 测真实 halt 路径）。
    red_line_id 也每轮递增 · 保证每 round 走真 halt_target.halt。
    """
    loop = asyncio.new_event_loop()

    counter = {"n": 0}

    def _round() -> None:
        counter["n"] += 1
        pid = "pid-bench"
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=MockHardHaltTarget(),
            event_bus=EventBusStub(),
        )
        signal = _make_signal(pid, f"redline-bench-{counter['n']}")
        loop.run_until_complete(consumer.consume(signal))

    # bench 跑 · pytest-benchmark 自动取多个 round
    benchmark.pedantic(
        _round,
        iterations=5,
        rounds=50,
        warmup_rounds=2,
    )

    loop.close()

    # P99 · stats.stats.data 是每次 round 的耗时（秒）
    data = sorted(benchmark.stats.stats.data)
    assert len(data) >= 20, f"rounds 太少 · len={len(data)}"
    # P99 索引
    p99_idx = max(0, int(len(data) * 0.99) - 1)
    p99_sec = data[p99_idx]
    p99_ms = p99_sec * 1000.0

    assert p99_ms <= HALT_SLO_MS, (
        f"HRL-05 violated · P99={p99_ms:.3f}ms > {HALT_SLO_MS}ms · "
        f"release blocker · data_len={len(data)}"
    )


@pytest.mark.perf
def test_TC_WP06_IC15_BENCH_MEAN_UNDER_SLO(benchmark) -> None:
    """TC-WP06-IC15-BENCH-MEAN · mean ≤ SLO · 用 benchmark mean 做次级防线。"""
    loop = asyncio.new_event_loop()

    counter = {"n": 0}

    def _round() -> None:
        counter["n"] += 1
        pid = "pid-bench-mean"
        consumer = IC15Consumer(
            session_pid=pid,
            halt_target=MockHardHaltTarget(),
            event_bus=EventBusStub(),
        )
        signal = _make_signal(pid, f"redline-mean-{counter['n']}")
        loop.run_until_complete(consumer.consume(signal))

    benchmark.pedantic(
        _round,
        iterations=5,
        rounds=30,
        warmup_rounds=2,
    )

    loop.close()
    mean_ms = benchmark.stats.stats.mean * 1000.0
    assert mean_ms <= HALT_SLO_MS, f"mean={mean_ms:.3f}ms > {HALT_SLO_MS}ms"
