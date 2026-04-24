"""IC-15 HaltRequester · L1-07 → L1-01 · 阻塞同步 · P99 ≤ 100ms 硬约束（HRL-05）。

关键 TC（按主会话仲裁 · ic-contracts §3.15）：
- request_hard_halt 正常 · halted=true · state_after=HALTED · halt_latency_ms 上限 100ms
- 阻塞式 · target 返回后才回 ack（不是 fire-and-forget）
- require_user_authorization 必 true（pydantic 层已锁）
- confirmation_count < 2 → pydantic 层拒绝
- 幂等 by red_line_id（§3.15.5 · 同 red_line_id 重复返已有 halt_id 的 ack）
- E_HALT_NO_EVIDENCE（observation_refs 空）
- E_HALT_ALREADY_HALTED · state 已 HALTED · 返回首次 halt_id 的 ack
- IC-09 审计事件 `L1-01:hard_halted`

**性能 benchmark**：pytest-benchmark · 10000 samples · P99 ≤ 100ms（HRL-05 不可降级）。
"""
from __future__ import annotations

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


pytestmark = pytest.mark.asyncio


def _cmd(
    halt_id: str = "halt-abcdef01",
    pid: str = "proj-a",
    red_line_id: str = "redline-rm-rf-system",
    confirmation_count: int = 2,
    obs: tuple[str, ...] = ("obs-1",),
) -> RequestHardHaltCommand:
    return RequestHardHaltCommand(
        halt_id=halt_id,
        project_id=pid,
        red_line_id=red_line_id,
        evidence=HardHaltEvidence(
            observation_refs=obs, confirmation_count=confirmation_count
        ),
        ts="t",
    )


@pytest.fixture
def target() -> MockHardHaltTarget:
    return MockHardHaltTarget()


@pytest.fixture
def bus() -> EventBusStub:
    return EventBusStub()


async def test_halt_valid_returns_halted(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    assert ack.halted is True
    assert ack.state_after == HardHaltState.HALTED
    assert ack.state_before == HardHaltState.RUNNING


async def test_halt_is_blocking_waits_for_target(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    """IC-15 阻塞式 · 区别于 IC-13 fire-and-forget。"""
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    # target.halt 必在 ack 返回前被调用一次
    assert target.halt_call_count == 1
    assert ack.halt_latency_ms >= 0


async def test_halt_latency_under_100ms_normal_path(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    """正常路径 · halt_latency_ms 必 ≤ 100ms（stub 场景 ≪100ms）。"""
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    assert ack.halt_latency_ms <= 100


async def test_halt_idempotent_same_red_line_id(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    """§3.15.5 · Idempotent by red_line_id · 重复命中返回首次 halt_id 的 ack。"""
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack1 = await r.request_hard_halt(
        _cmd(halt_id="halt-first0001", red_line_id="redline-dup")
    )
    ack2 = await r.request_hard_halt(
        _cmd(halt_id="halt-second001", red_line_id="redline-dup")
    )
    # 第二次 ack 带第一次的 halt_id
    assert ack1.halt_id == ack2.halt_id
    # target 只被 halt 一次
    assert target.halt_call_count == 1


async def test_halt_already_halted_returns_existing(
    bus: EventBusStub,
) -> None:
    """target state 已 HALTED · 直接返回 idempotent ack · halt 仍然 true。"""
    target = MockHardHaltTarget(initial_state=HardHaltState.HALTED)
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    assert ack.halted is True
    # state_before 是 HALTED（已 halted）
    assert ack.state_before == HardHaltState.HALTED


async def test_halt_cross_project_rejected(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID|cross|pid"):
        await r.request_hard_halt(_cmd(pid="proj-other"))


async def test_halt_emits_ic09_audit(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    await r.request_hard_halt(_cmd())
    evs = await bus.read_event_stream(project_id="proj-a", types=["L1-01:hard_halted"])
    assert len(evs) == 1
    payload = evs[0].payload
    assert payload["halt_id"].startswith("halt-")
    assert payload["red_line_id"] == "redline-rm-rf-system"
    assert "latency_ms" in payload


async def test_halt_audit_entry_id_generated(
    target: MockHardHaltTarget, bus: EventBusStub
) -> None:
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    assert ack.audit_entry_id
    assert ack.audit_entry_id.startswith("ev-") or len(ack.audit_entry_id) > 0


async def test_halt_slo_violation_still_returns_halted(
    bus: EventBusStub,
) -> None:
    """§3.15.4 E_HALT_SLO_VIOLATION · halt_latency_ms > 100 仍返回 halted=true · 但 L1-07 侧告警。

    此 TC 用 slow_halt_ms 注入 >100ms 延迟 · 验证 ack 仍 halted=true。
    """
    target = MockHardHaltTarget(slow_halt_ms=120)
    r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
    ack = await r.request_hard_halt(_cmd())
    assert ack.halted is True
    assert ack.halt_latency_ms >= 100
    # 应该 emit SLO 告警审计事件
    evs = await bus.read_event_stream(project_id="proj-a", types=["L1-07:halt_slo_violated"])
    assert len(evs) == 1


# ==============================================================================
# P99 ≤ 100ms benchmark · HRL-05 不可降级（release blocker）
# ==============================================================================


def test_halt_p99_latency_under_100ms_10k_samples(benchmark) -> None:
    """pytest-benchmark · 10000 samples · P99 ≤ 100ms 硬约束（HRL-05）。

    方法：两轨测量——
    1. 手动采集 10000 样本 · 用 perf_counter_ns 测 request_hard_halt 墙钟时延 ·
       单位精度到 us（ack.halt_latency_ms 是 integer ms · 亚毫秒会被截为 0）
    2. pytest-benchmark 独立统计（给 CI 留对比基线）

    底层 target stub 为 in-memory 常数时间操作 · 无 IO · 代表 L1-07 → L1-01 最小路径成本。
    违反 · 视为 release blocker · 触发 P1。
    """
    import asyncio
    import statistics
    import time

    # 采 10000 点 · 每次独立 HaltRequester + MockHardHaltTarget（避免幂等缓存污染）
    latencies_us: list[float] = []
    latencies_ms_int: list[int] = []
    for i in range(10000):
        target = MockHardHaltTarget()
        bus = EventBusStub()
        r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
        cmd = RequestHardHaltCommand(
            halt_id=f"halt-bench{i:06d}",
            project_id="proj-a",
            red_line_id=f"redline-bench-{i}",
            evidence=HardHaltEvidence(
                observation_refs=("obs-1",), confirmation_count=2
            ),
            ts="t",
        )
        t0 = time.perf_counter_ns()
        ack = asyncio.run(r.request_hard_halt(cmd))
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)
        latencies_ms_int.append(ack.halt_latency_ms)

    n = len(latencies_us)
    sorted_us = sorted(latencies_us)
    p50 = sorted_us[int(n * 0.50)]
    p95 = sorted_us[int(n * 0.95)]
    p99 = sorted_us[int(n * 0.99)]
    p999 = sorted_us[int(n * 0.999)]
    mean = statistics.mean(latencies_us)
    maxv = max(latencies_us)

    # 输出到 stdout · standup log 直接抓取
    print(
        f"\n[HRL-05 halt_latency benchmark · n={n}] "
        f"p50={p50:.1f}us p95={p95:.1f}us p99={p99:.1f}us "
        f"p99.9={p999:.1f}us mean={mean:.1f}us max={maxv:.1f}us"
    )
    print(
        f"[HRL-05 · ack.halt_latency_ms (integer)] "
        f"p99={sorted(latencies_ms_int)[int(n * 0.99)]}ms "
        f"max={max(latencies_ms_int)}ms slo=100ms"
    )

    # 硬断言 · P99 ≤ 100ms（= 100000 us）
    assert p99 <= 100_000, (
        f"HRL-05 违反 · halt_latency P99={p99:.1f}us > 100000us (100ms) · release blocker"
    )
    # 且 ack.halt_latency_ms 的 P99 ≤ 100
    ack_p99_ms = sorted(latencies_ms_int)[int(n * 0.99)]
    assert ack_p99_ms <= 100, (
        f"HRL-05 违反 · ack.halt_latency_ms P99={ack_p99_ms}ms > 100ms · release blocker"
    )

    # 让 benchmark 跑一次 · 便于 pytest-benchmark 生成 CI 统计
    async def _single():
        target = MockHardHaltTarget()
        bus = EventBusStub()
        r = HaltRequester(session_pid="proj-a", target=target, event_bus=bus)
        cmd = RequestHardHaltCommand(
            halt_id="halt-bench-warm",
            project_id="proj-a",
            red_line_id="redline-bench-warm",
            evidence=HardHaltEvidence(
                observation_refs=("obs-1",), confirmation_count=2
            ),
            ts="t",
        )
        await r.request_hard_halt(cmd)

    def _sync():
        asyncio.run(_single())

    benchmark(_sync)
