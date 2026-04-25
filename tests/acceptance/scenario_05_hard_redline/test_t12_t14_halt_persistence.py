"""Scenario 05 · T12-T14 · halt 持续性 (用户离线 / UI 不可达 / 跨 tick 仍 halt).

halt 状态的持久化测试:
- T12 用户离线 · halt 仍持续 · dispatch 持续被拒
- T13 UI 不可达 · halt marker 跨进程可见 (基于文件)
- T14 跨 tick · halt 状态在 multi-tick loop 中持久 · 一直 reject_count 累加
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus.halt_guard import HaltGuard
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_HALTED_REJECT,
    TickError,
)
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T12 · 用户离线 · halt 仍持续 · dispatch 一直被拒
# ============================================================================


async def test_t12_halt_persists_when_user_offline(
    halt_enforcer: HaltEnforcer,
    ic15_consumer: IC15Consumer,
    make_halt_signal,
    gwt: GWT,
) -> None:
    """T12 · halt 后用户离线 (没人 authorize) · 后续 1000 次 dispatch 全拒."""
    async with gwt("T12 · 用户离线场景 · halt 不自动解 · 持续拒 dispatch"):
        gwt.given("HaltEnforcer 接 IC-15 → HALTED")
        signal = make_halt_signal(red_line_id="HRL-01", halt_id="halt-t12-offline")
        await ic15_consumer.consume(signal)
        assert halt_enforcer.is_halted() is True

        gwt.when("模拟 1000 次 dispatch (假装 tick loop 一直跑 · 用户没在)")
        reject_count_start = halt_enforcer.reject_count
        for _ in range(1000):
            with pytest.raises(TickError) as exc:
                halt_enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_HALTED_REJECT

        gwt.then("reject_count 累加 1000 · halt 状态仍 active")
        assert halt_enforcer.reject_count == reject_count_start + 1000
        assert halt_enforcer.is_halted() is True
        # active_halt_id 不被覆盖
        assert halt_enforcer.active_halt_id == "halt-t12-offline"


# ============================================================================
# T13 · UI 不可达 · halt marker 跨进程文件持久 (基于 _halt.marker)
# ============================================================================


async def test_t13_halt_marker_persists_via_file(
    tmp_path: Path,
    gwt: GWT,
) -> None:
    """T13 · UI 进程死了 · halt marker 仍在文件系统 · 跨进程可见."""
    async with gwt("T13 · UI 不可达 · halt 跨进程文件持久"):
        gwt.given("HaltGuard 已写 marker 到磁盘")
        guard_dir = tmp_path / "_global"
        guard_dir.mkdir(parents=True)
        guard = HaltGuard(guard_dir)
        guard.mark_halt(
            reason="t13 ui unreachable test",
            source="L2-01:test:ui_dead",
            correlation_id="evt-test-t13",
        )

        gwt.when("模拟 UI 进程崩溃 → 起一个新 HaltGuard (新进程读 marker)")
        # 新 guard 实例 = 新进程的视角
        new_guard = HaltGuard(guard_dir)

        gwt.then("新进程读 marker · 看到 halt 仍 active")
        assert new_guard.is_halted() is True

        gwt.then("marker 内容可解析 · 含 reason / source")
        info = new_guard.load_halt_info()
        assert info is not None
        assert "t13 ui unreachable test" in info.get("reason", "")
        assert info.get("source", "") == "L2-01:test:ui_dead"
        assert info.get("correlation_id", "") == "evt-test-t13"


# ============================================================================
# T14 · 跨 tick · halt 在 multi-tick loop 中持久 · reject_count 持续累加
# ============================================================================


async def test_t14_halt_persists_across_multiple_ticks(
    halt_enforcer: HaltEnforcer,
    ic15_consumer: IC15Consumer,
    make_halt_signal,
    gwt: GWT,
) -> None:
    """T14 · halt 后 · 跨多 tick (模拟 100 tick loop iteration) 一直 active."""
    async with gwt("T14 · 跨 tick halt 持续 · 100 tick 中始终 HALTED"):
        gwt.given("HaltEnforcer 进入 HALTED · halt_id=halt-t14-persistent")
        signal = make_halt_signal(red_line_id="HRL-01", halt_id="halt-t14-persistent")
        await ic15_consumer.consume(signal)

        gwt.when("跑 100 次 tick (模拟 10 秒 loop · 100ms interval)")
        # 每 tick 头部 enforcer.is_halted() 必须返 True
        snapshot_states = []
        for tick_idx in range(100):
            snapshot_states.append({
                "tick": tick_idx,
                "is_halted": halt_enforcer.is_halted(),
                "tick_state": halt_enforcer.as_tick_state().value,
                "active_halt_id": halt_enforcer.active_halt_id,
            })

        gwt.then("100 tick 中 · 每次 is_halted=True · active_halt_id 恒等")
        for snap in snapshot_states:
            assert snap["is_halted"] is True
            assert snap["tick_state"] == "HALTED"
            assert snap["active_halt_id"] == "halt-t14-persistent"

        gwt.then("二次 IC-15 同 red_line_id (HRL-01) · idempotent_hit · 不破坏 active_halt_id")
        signal2 = make_halt_signal(red_line_id="HRL-01", halt_id="halt-t14-second-call")
        ack2 = await ic15_consumer.consume(signal2)
        assert ack2.idempotent_hit is True
        assert ack2.halt_id == "halt-t14-persistent"  # 返第一条
        # active_halt_id 仍是首条
        assert halt_enforcer.active_halt_id == "halt-t14-persistent"
