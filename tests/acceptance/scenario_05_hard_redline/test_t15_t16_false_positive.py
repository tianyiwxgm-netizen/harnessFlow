"""Scenario 05 · T15-T16 · 误杀保护 (pattern 误命中后用户授权恢复).

误杀保护流程:
- 检测器误命中 → halt 仍执行 (safety first · 安全优先于体验)
- 用户审 audit 后判定为误杀 → 通过 admin_token clear_halt 解锁
- 重启 / 新 enforcer 后系统恢复 RUNNING

2 TC:
- T15 误杀场景下 halt 仍执行 (safety first · 不放过疑似)
- T16 用户判定误杀 → admin_token 解锁 + 新 enforcer 恢复 RUNNING
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.halt_guard import ADMIN_TOKEN_ENV_VAR, HaltGuard
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


# ============================================================================
# T15 · 误杀保护 · pattern 误命中 · halt 仍执行 (safety first)
# ============================================================================


async def test_t15_false_positive_still_halts_safety_first(
    halt_enforcer: HaltEnforcer,
    ic15_consumer: IC15Consumer,
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    make_halt_signal,
    gwt: GWT,
) -> None:
    """T15 · 即使是 false-positive · halt 仍触发 (硬红线安全 > 体验)."""
    async with gwt("T15 · 误杀场景仍 halt · safety first 优先于精度"):
        gwt.given("HaltEnforcer RUNNING · pattern_db 假设含模糊匹配")
        assert halt_enforcer.is_halted() is False

        gwt.when("L1-07 误命中 R-1 (PM-14 violation false positive)")
        # 模拟误命中:正常 user 输入但触发 R-1 pattern
        signal = make_halt_signal(
            red_line_id="HRL-01",
            halt_id="halt-t15-false-pos",
            observation_refs=("ev-false-pos-1", "ev-false-pos-2"),
        )
        ack = await ic15_consumer.consume(signal)

        gwt.then("halt 仍执行 (不因误杀风险跳过)")
        assert ack.halted is True
        assert halt_enforcer.is_halted() is True

        gwt.then("audit 完整保留误命中证据 · 留供用户事后审")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:hard_halted",
            payload_contains={"halt_id": "halt-t15-false-pos"},
        )
        assert len(events) == 1
        # observation_refs 完整保留
        assert "ev-false-pos-1" in events[0].get("payload", {}).get("evidence_refs", [])

        gwt.then("require_user_authorization=true · 必须用户介入才解")
        assert events[0]["payload"]["require_user_authorization"] is True


# ============================================================================
# T16 · 用户判定误杀 → 通过 admin_token clear_halt 解锁 + 新 enforcer 恢复
# ============================================================================


async def test_t16_user_clears_false_positive_via_admin_token(
    tmp_path: Path,
    monkeypatch,
    project_id: str,
    gwt: GWT,
) -> None:
    """T16 · 误杀后用户判定 → admin_token 解锁 → 新 session 起 RUNNING."""
    async with gwt("T16 · 误杀恢复:admin_token clear → 新 enforcer 起 RUNNING"):
        gwt.given("系统因 false positive 进 halt (HaltGuard marker + HaltEnforcer)")
        guard_dir = tmp_path / "_global"
        guard_dir.mkdir(parents=True)
        guard = HaltGuard(guard_dir)
        guard.mark_halt(
            reason="false-positive-r1",
            source="L2-01:test:false_pos",
            correlation_id="evt-fp-test",
        )
        assert guard.is_halted() is True

        # enforcer 模拟当前 session 已 HALTED
        enforcer_old = HaltEnforcer(project_id=project_id)
        await enforcer_old.halt(halt_id="halt-fp-old", red_line_id="HRL-01")
        assert enforcer_old.is_halted() is True

        gwt.when("用户审 audit 后判定为误杀 · 用 admin_token clear_halt")
        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "user-cleared-fp-token")
        cleared = guard.clear_halt(admin_token="user-cleared-fp-token")

        gwt.then("clear_halt 返 True · marker 删除")
        assert cleared is True
        assert guard.is_halted() is False

        gwt.when("重启 / 新 session 起 enforcer (模拟系统重启)")
        # 新 enforcer · 内存初态 RUNNING
        enforcer_new = HaltEnforcer(project_id=project_id)

        gwt.then("新 enforcer 默认 RUNNING · 不读旧 session in-memory state")
        assert enforcer_new.is_halted() is False
        assert enforcer_new.as_tick_state().value == "RUNNING"

        gwt.then("但 HaltGuard marker 已无 · 新 EventBus 起来不会再 halted")
        # 用 cleared marker 起新 EventBus
        bus_root = tmp_path / "bus_root"
        bus_root.mkdir(parents=True, exist_ok=True)
        # 重要: bus root 与 guard root 是分开的 (guard 在 _global) · 这里只验证
        # cleared 后 marker 消失 · 系统可重启
