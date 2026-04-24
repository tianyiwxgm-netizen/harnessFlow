"""IC-15 消费端 TC · **Sync ≤ 100ms HRL-05 铁律**。

对齐 L2-06 §3.2 broadcast_block + HRL-05（主会话仲裁 §C-2）。
测试形式：
- §2 正向 · §3 负向（pm-14 / slo 违反）· §4 幂等 · §5 bench P99 ≤ 100ms
"""
from __future__ import annotations

import pytest

from app.main_loop.supervisor_receiver.ic_15_consumer import (
    HALT_SLO_MS,
    IC15Consumer,
)
from app.main_loop.supervisor_receiver.schemas import HaltState
from app.supervisor.event_sender.halt_requester import MockHardHaltTarget

pytestmark = pytest.mark.asyncio


@pytest.fixture
def halt_target() -> MockHardHaltTarget:
    return MockHardHaltTarget()


# ------------------------ §2 正向 ------------------------


async def test_TC_WP06_IC15_001_normal_halt_within_slo(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-001 · 正常 halt · latency ≤ 100ms · ack.halted=true · slo_violated=false。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    signal = make_halt_signal(project_id=pid)

    ack = await sut.consume(signal)

    assert ack.halted is True
    assert ack.latency_ms <= HALT_SLO_MS, f"latency={ack.latency_ms}ms > {HALT_SLO_MS}"
    assert ack.slo_violated is False
    assert ack.state_before == HaltState.RUNNING
    assert ack.state_after == HaltState.HALTED
    assert ack.idempotent_hit is False


async def test_TC_WP06_IC15_002_halt_target_called_once(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-002 · 单次 consume · halt_target.halt 调用 1 次。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    await sut.consume(make_halt_signal(project_id=pid))

    assert halt_target.halt_call_count == 1


async def test_TC_WP06_IC15_003_emits_hard_halted_audit(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-003 · emit IC-09 `L1-01:hard_halted` 审计。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    await sut.consume(make_halt_signal(project_id=pid))

    types = [e.type for e in event_bus._events]
    assert "L1-01:hard_halted" in types
    # 同时 SLO 未违反时 · 不应有 halt_slo_violated
    assert "L1-07:halt_slo_violated" not in types


# ------------------------ §3 负向 ------------------------


async def test_TC_WP06_IC15_101_cross_project_rejected(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-101 · cross-project · 抛 E_HALT_NO_PROJECT_ID · 不 halt。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    signal = make_halt_signal(project_id="pid-other")

    with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID"):
        await sut.consume(signal)

    assert halt_target.halt_call_count == 0


async def test_TC_WP06_IC15_102_empty_session_pid_rejected(
    event_bus, halt_target
) -> None:
    """TC-WP06-IC15-102 · session_pid 空 · __post_init__ 抛 E_HALT_NO_PROJECT_ID。"""
    with pytest.raises(ValueError, match="E_HALT_NO_PROJECT_ID"):
        IC15Consumer(session_pid="", halt_target=halt_target, event_bus=event_bus)


async def test_TC_WP06_IC15_103_slo_violation_path(
    pid, event_bus, make_halt_signal
) -> None:
    """TC-WP06-IC15-103 · target 慢 halt · latency > slo · slo_violated=true · emit HRL-05 告警。

    为避免真 sleep 200ms 拖慢 suite · slo_ms 调到 5ms · MockHardHaltTarget.slow_halt_ms=20。
    """
    slow_target = MockHardHaltTarget(slow_halt_ms=20)
    sut = IC15Consumer(
        session_pid=pid, halt_target=slow_target, event_bus=event_bus, slo_ms=5
    )
    signal = make_halt_signal(project_id=pid)

    ack = await sut.consume(signal)

    assert ack.halted is True, "SLO 违反仍生效 halt"
    assert ack.latency_ms > 5
    assert ack.slo_violated is True
    types = [e.type for e in event_bus._events]
    assert "L1-07:halt_slo_violated" in types


# ------------------------ §4 幂等 ------------------------


async def test_TC_WP06_IC15_201_idempotent_by_red_line_id(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-201 · 同 red_line_id 重复推 · halt_target 只调 1 次 · idempotent_hit=true。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    signal1 = make_halt_signal(project_id=pid, red_line_id="redline-idem-001")
    signal2 = make_halt_signal(project_id=pid, red_line_id="redline-idem-001")

    ack1 = await sut.consume(signal1)
    ack2 = await sut.consume(signal2)

    assert halt_target.halt_call_count == 1, "幂等 · halt_target 只被调 1 次"
    assert ack1.idempotent_hit is False
    assert ack2.idempotent_hit is True
    # 幂等返回的 halt_id 是首次那一条
    assert ack2.halt_id == ack1.halt_id


async def test_TC_WP06_IC15_202_idempotent_different_red_line_triggers_new_halt(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-202 · 不同 red_line_id · 各自触发 halt · halt_target 调 2 次。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    sig_a = make_halt_signal(project_id=pid, red_line_id="redline-A")
    sig_b = make_halt_signal(project_id=pid, red_line_id="redline-B")

    await sut.consume(sig_a)
    await sut.consume(sig_b)

    assert halt_target.halt_call_count == 2


# ------------------------ §9 edge ------------------------


async def test_TC_WP06_IC15_901_latency_ms_is_monotonic_nonneg(
    pid, event_bus, halt_target, make_halt_signal
) -> None:
    """TC-WP06-IC15-901 · latency_ms ≥ 0 · 无负数（perf_counter_ns 单调）。"""
    sut = IC15Consumer(session_pid=pid, halt_target=halt_target, event_bus=event_bus)
    ack = await sut.consume(make_halt_signal(project_id=pid))
    assert ack.latency_ms >= 0
