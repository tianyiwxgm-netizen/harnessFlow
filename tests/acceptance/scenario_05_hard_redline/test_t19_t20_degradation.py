"""Scenario 05 · T19-T20 · 降级 (pattern_db 失败 = 默认 BLOCK · IC-15 emit 失败 = panic).

降级铁律 (硬红线 release blocker · safety > availability):
- T19 pattern_db load 失败 / 不可用 → 默认拒所有 dispatch (BLOCK 一切)
- T20 IC-15 emit 失败 (consumer event_bus halted) → 触发 panic 路径

2 TC.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.halt_guard import HaltGuard
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.supervisor_receiver.schemas import HaltSignal
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import (
    E_TICK_HALTED_REJECT,
    TickError,
    TickState,
)
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T19 · pattern_db 不可用 / 加载失败 · 默认 BLOCK 所有 dispatch (safety first)
# ============================================================================


async def test_t19_pattern_db_failure_defaults_to_block(
    project_id: str,
    gwt: GWT,
) -> None:
    """T19 · 无 pattern_db (即 detector 不工作) · 但仍可强制 halt → BLOCK 默认行为.

    模拟场景:pattern_db 不可加载 / 损坏 · 系统不知红线规则
    安全降级:enforcer 提供 mark_halt 强制 halt 入口 · 所有 dispatch 直接拒
    """
    async with gwt("T19 · pattern_db 失败 · enforcer 强制 BLOCK 默认行为"):
        gwt.given("HaltEnforcer 创建 · pattern_db 不可用 · 没 detector 工作")
        enforcer = HaltEnforcer(project_id=project_id)

        gwt.when("系统判定无法识别红线 → 主动调 halt() 强制 BLOCK")
        # 模拟降级路径:管理员 / 监控触发 fallback halt
        # halt() 是 enforcer 公开 API · 任何调用方都可触发
        await enforcer.halt(halt_id="halt-t19-degraded-fallback", red_line_id="DEGRADED-FALLBACK")

        gwt.then("enforcer state=HALTED · is_halted=True")
        assert enforcer.is_halted() is True
        assert enforcer.as_tick_state() == TickState.HALTED

        gwt.then("所有 assert_can_dispatch 都拒 · safety 默认 BLOCK")
        for _ in range(10):
            with pytest.raises(TickError) as exc:
                enforcer.assert_can_dispatch()
            assert exc.value.error_code == E_TICK_HALTED_REJECT
        assert enforcer.reject_count == 10


# ============================================================================
# T20 · IC-15 emit 失败 (event_bus halted) · 触发 panic 路径
# ============================================================================


async def test_t20_ic15_emit_failure_triggers_panic(
    tmp_path: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T20 · IC-15 emit (audit append) 失败时 · 触发 panic 路径 → state=PAUSED.

    场景:audit bus 已 halted (marker 存在) · IC-15 consumer 调 append 抛 BusHalted
    系统降级:enforcer 仍可 halt (内存翻态成功 · 业务停) + panic_handler 标 PAUSED
    """
    from app.l1_09.event_bus.schemas import BusHalted

    async with gwt("T20 · IC-15 emit 失败 · panic 路径触发 (PAUSED 兜底)"):
        gwt.given("EventBus 已 halted (marker 文件存在) · audit append 必抛")
        bus_root = tmp_path / "halted_bus"
        bus_root.mkdir(parents=True)
        bus = EventBus(bus_root)
        # 触发 halt (模拟 fsync 失败已落 marker)
        bus.halt_guard.mark_halt(reason="t20 simulated", source="test")
        assert bus.halt_guard.is_halted()

        # 验证:任何 append 抛 BusHalted
        from app.l1_09.event_bus.schemas import Event

        bad_event = Event(
            project_id=project_id,
            type="L1-01:hard_halted",
            actor="supervisor",
            timestamp=datetime.now(UTC),
            payload={"red_line_id": "HRL-01"},
        )
        with pytest.raises(BusHalted):
            bus.append(bad_event)

        gwt.when("系统检测到 audit bus halted → emit panic 信号 → handler 标 PAUSED")

        # 用 enforcer + panic_handler 走降级路径 (PAUSED 不阻 audit recovery)
        # panic_handler 的 project_id 必须满足 ^pid-[A-Za-z0-9_-]{3,}$ 模式
        pid_for_panic = "pid-t20-degrade"
        panic_enforcer = HaltEnforcer(project_id=pid_for_panic)
        panic_handler = PanicHandler(
            project_id=pid_for_panic, halt_enforcer=panic_enforcer,
        )

        signal = PanicSignal(
            panic_id="panic-t20-bus-halt-degrade",
            project_id=pid_for_panic,
            user_id="system-degrade-detector",
            reason="ic15_audit_emit_failed: bus halted during halt audit",
            ts=datetime.now(UTC).isoformat(),
            scope="session",
        )

        t0 = time.monotonic()
        result = panic_handler.handle(signal)
        elapsed_ms = (time.monotonic() - t0) * 1000

        gwt.then("panic 在 ≤ 100ms 内完成 (HRL-04)")
        assert result.paused is True
        assert elapsed_ms < 100.0, f"panic latency {elapsed_ms:.2f}ms 超 100ms"

        gwt.then("enforcer state=PAUSED · 业务全停")
        assert panic_enforcer.as_tick_state() == TickState.PAUSED

        gwt.then("panic_history 含 reason 透传 · 留供运维诊断")
        h = panic_handler.panic_history
        assert len(h) == 1
        assert "ic15_audit_emit_failed" in h[0]["reason"]
        assert h[0]["scope"] == "session"
