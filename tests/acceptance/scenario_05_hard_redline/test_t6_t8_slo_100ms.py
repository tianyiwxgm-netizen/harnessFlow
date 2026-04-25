"""Scenario 05 · T6-T8 · 100ms SLO 三场景 (baseline / 持续负载 / 冷启动).

每 TC 用 perf_helpers.assert_p99_under 强校验 P99 ≤ 100ms.

- T6 baseline   单次 halt · 干净环境 · P99 ≤ 100ms
- T7 持续负载    50 次连续 halt (5 红线 × 10 round) · 检 SLO 不退化
- T8 冷启动      首次 EventBus 初始化 + 首 halt · P99 ≤ 100ms
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from tests.shared.gwt_helpers import GWT
from tests.shared.perf_helpers import LatencyStats, assert_p99_under, measure_async


# ============================================================================
# T6 · 100ms SLO baseline · 单次 halt
# ============================================================================


async def test_t6_slo_baseline_single_halt(
    ic15_consumer: IC15Consumer,
    halt_enforcer: HaltEnforcer,
    make_halt_signal,
    gwt: GWT,
) -> None:
    """T6 · baseline 单次 halt · P99 ≤ 100ms."""
    async with gwt("T6 · 100ms SLO baseline · 单次 halt 干净环境"):
        gwt.given("scheduler RUNNING · pattern_db loaded · audit empty")
        assert halt_enforcer.is_halted() is False

        gwt.when("发 1 条 IC-15 request_hard_halt (HRL-01)")
        signal = make_halt_signal(
            red_line_id="HRL-01", halt_id="halt-t6-baseline",
        )
        sample = await measure_async(ic15_consumer.consume(signal))

        gwt.then("总链 elapsed_ms ≤ 100ms (HRL-05 release blocker)")
        assert sample.payload.halted is True
        assert sample.elapsed_ms < 100.0, (
            f"baseline halt elapsed={sample.elapsed_ms:.2f}ms 超 100ms"
        )
        # ack 内部计的 latency 应远小于 elapsed (含 audit + adapter 开销)
        assert sample.payload.latency_ms <= sample.elapsed_ms


# ============================================================================
# T7 · 持续负载 · 50 次 halt (10 round × 5 红线) · P99 不退化
# ============================================================================


async def test_t7_slo_under_load_50_halts(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T7 · 50 次连续 halt · P99 ≤ 100ms · 不退化.

    每次都是干净 enforcer + consumer (避免 consumer 幂等 cache 命中早返回).
    单条 halt P99 ≤ 100ms 是硬约束.
    """
    from datetime import UTC, datetime

    from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
    from app.main_loop.supervisor_receiver.schemas import HaltSignal
    from app.supervisor.event_sender.schemas import (
        HardHaltEvidence,
        RequestHardHaltCommand,
    )
    from tests.acceptance.scenario_05_hard_redline.conftest import (
        _AsyncEventBusAdapter,
    )

    async with gwt("T7 · 50 halt 持续负载 · P99 ≤ 100ms 不退化"):
        gwt.given("real_event_bus 接受 50 条独立 hard_halted 落盘")
        adapter = _AsyncEventBusAdapter(real_event_bus, project_id)

        gwt.when("循环 50 次 · 每次 fresh enforcer + consumer · 同样的 5 红线轮换")
        samples = []
        redlines = ["HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"]
        for round_idx in range(10):
            for r_idx, hrl in enumerate(redlines):
                # fresh enforcer + consumer (避 idempotent cache)
                enforcer = HaltEnforcer(project_id=project_id)
                consumer = IC15Consumer(
                    session_pid=project_id,
                    halt_target=enforcer,
                    event_bus=adapter,
                )
                halt_id = f"halt-t7-r{round_idx}-i{r_idx}"
                cmd = RequestHardHaltCommand(
                    halt_id=halt_id,
                    project_id=project_id,
                    red_line_id=hrl,
                    evidence=HardHaltEvidence(
                        observation_refs=(f"ev-{halt_id}-1", f"ev-{halt_id}-2"),
                        confirmation_count=2,
                    ),
                    require_user_authorization=True,
                    ts=datetime.now(UTC).isoformat(),
                )
                signal = HaltSignal.from_command(cmd, received_at_ms=0)
                sample = await measure_async(consumer.consume(signal))
                assert sample.payload.halted is True
                samples.append(sample)

        gwt.then(f"P99 ≤ 100ms · 50 samples · {len(samples)=}")
        assert len(samples) == 50
        stats = assert_p99_under(samples, budget_ms=100.0, metric_name="halt_chain_p99")
        # 额外 sanity:max < 200ms (即使有 GC 抖动也不应超太多)
        assert stats.max < 200.0, f"max latency {stats.max}ms 异常 stats={stats.summary()}"


# ============================================================================
# T8 · 冷启动 · 首次 EventBus init + 首 halt · P99 ≤ 100ms
# ============================================================================


async def test_t8_slo_cold_start(
    tmp_path: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T8 · 冷启动场景 · 全新 EventBus + 全新 enforcer + 首次 halt · P99 ≤ 100ms.

    模拟系统重启后第一次 halt:
    - 全新 tmp 目录 (含 _global / projects 创建)
    - 全新 HaltEnforcer (内存初态)
    - 全新 IC15Consumer (无 idempotent cache)
    """
    from datetime import UTC, datetime

    from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
    from app.main_loop.supervisor_receiver.schemas import HaltSignal
    from app.supervisor.event_sender.schemas import (
        HardHaltEvidence,
        RequestHardHaltCommand,
    )
    from tests.acceptance.scenario_05_hard_redline.conftest import (
        _AsyncEventBusAdapter,
    )

    async with gwt("T8 · 冷启动 · 全新 EventBus init + 首 halt ≤ 100ms"):
        gwt.given("tmp_path 干净 · 没有 events.jsonl / meta.json / halt.marker")
        cold_root = tmp_path / "cold_bus"
        cold_root.mkdir(parents=True)

        gwt.when("初始化 EventBus + enforcer + consumer + 首 halt")

        # 把 init + 首次 consume 当一个端到端事件测延时
        async def cold_start_chain() -> dict:
            bus = EventBus(cold_root)
            enforcer = HaltEnforcer(project_id=project_id)
            adapter = _AsyncEventBusAdapter(bus, project_id)
            consumer = IC15Consumer(
                session_pid=project_id,
                halt_target=enforcer,
                event_bus=adapter,
            )
            cmd = RequestHardHaltCommand(
                halt_id="halt-t8-cold-start",
                project_id=project_id,
                red_line_id="HRL-01",
                evidence=HardHaltEvidence(
                    observation_refs=("ev-cold-1", "ev-cold-2"),
                    confirmation_count=2,
                ),
                require_user_authorization=True,
                ts=datetime.now(UTC).isoformat(),
            )
            signal = HaltSignal.from_command(cmd, received_at_ms=0)
            return await consumer.consume(signal)

        sample = await measure_async(cold_start_chain())

        gwt.then("冷启动总链 elapsed_ms ≤ 100ms (含 EventBus init 开销)")
        assert sample.payload.halted is True
        assert sample.elapsed_ms < 100.0, (
            f"cold start chain elapsed={sample.elapsed_ms:.2f}ms 超 100ms"
        )
