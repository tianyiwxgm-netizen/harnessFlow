"""Scenario 05 · T9-T11 · 用户授权放行链 (AUTHORIZE 有效 / 失效 / 过期).

硬红线一旦命中 · 必须用户 IC-17 user_intervene authorize 才解 halt.
HALTED 是不可逆 (只能 panic→PAUSED 才可被 user resume; HALTED 仍 active).

3 TC:
- T9  AUTHORIZE 有效 token · halt 仍持久 (HALTED 不被一般 resume 解除)
- T10 token 失效 (token 不匹配) · clear_halt 拒
- T11 token 过期 (HARNESS_ADMIN_TOKEN 未配 = 安全兜底拒)
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
from tests.shared.ic_assertions import assert_ic_09_emitted


# ============================================================================
# T9 · AUTHORIZE 有效 token · halt 不被普通 resume 解除 (HALTED 不可逆)
# ============================================================================


async def test_t9_authorize_valid_does_not_clear_hard_halt(
    halt_enforcer: HaltEnforcer,
    ic15_consumer: IC15Consumer,
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    make_halt_signal,
    gwt: GWT,
) -> None:
    """T9 · halt 后 · 普通 panic_handler.resume() 不能解 HALTED (HALTED 不可逆).

    HALTED 与 PAUSED 严格区分:
    - PAUSED 可被 user resume → RUNNING
    - HALTED 一旦进入 · resume 无效 · 仍 HALTED
    """
    async with gwt("T9 · AUTHORIZE 有效仍不解 HALTED · 硬红线不可逆"):
        gwt.given("HaltEnforcer 收 IC-15 → HALTED")
        signal = make_halt_signal(red_line_id="HRL-01", halt_id="halt-t9-authorize")
        ack = await ic15_consumer.consume(signal)
        assert ack.halted is True
        assert halt_enforcer.is_halted() is True

        gwt.when("调 halt_enforcer.clear_panic() (PAUSED 用) · 也试调 mark_panic")
        # clear_panic 只清 PAUSED · 对 HALTED 无影响
        halt_enforcer.clear_panic()

        gwt.then("HALTED 不被 clear_panic 影响 · 仍 HALTED")
        assert halt_enforcer.is_halted() is True
        assert halt_enforcer.as_tick_state().value == "HALTED"

        gwt.then("audit 仍记录 require_user_authorization=true")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-01:hard_halted",
            payload_contains={"require_user_authorization": True},
        )
        assert len(events) >= 1


# ============================================================================
# T10 · admin_token 不匹配 · halt_guard.clear_halt 拒
# ============================================================================


async def test_t10_authorize_invalid_token_rejected(
    tmp_path: Path,
    monkeypatch,
    gwt: GWT,
) -> None:
    """T10 · admin_token mismatch · clear_halt 返 False · halt 仍 active."""
    async with gwt("T10 · admin_token 不匹配 · clear_halt 拒"):
        gwt.given("HaltGuard 已 mark_halt + admin_token env 设为 expected-secret")
        guard_dir = tmp_path / "_global"
        guard_dir.mkdir(parents=True)
        guard = HaltGuard(guard_dir)
        guard.mark_halt(reason="test halt", source="test")
        assert guard.is_halted() is True

        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "expected-secret-token")

        gwt.when("调 clear_halt(admin_token='wrong-token')")
        cleared = guard.clear_halt(admin_token="wrong-token")

        gwt.then("clear_halt 返 False · halt marker 仍存在")
        assert cleared is False
        assert guard.is_halted() is True

        gwt.then("正确 token 才能解锁")
        cleared_ok = guard.clear_halt(admin_token="expected-secret-token")
        assert cleared_ok is True
        assert guard.is_halted() is False


# ============================================================================
# T11 · admin_token 未配置 (env 缺) · clear_halt 安全兜底拒
# ============================================================================


async def test_t11_authorize_token_unset_safety_reject(
    tmp_path: Path,
    monkeypatch,
    gwt: GWT,
) -> None:
    """T11 · admin_token env 未设 · 任何 token 都被拒 (安全兜底)."""
    async with gwt("T11 · admin_token env 未配 · 安全兜底拒任何解锁"):
        gwt.given("HaltGuard 已 mark_halt · 但 HARNESS_ADMIN_TOKEN env 未设")
        guard_dir = tmp_path / "_global"
        guard_dir.mkdir(parents=True)
        guard = HaltGuard(guard_dir)
        guard.mark_halt(reason="test halt", source="test")
        # 显式删除 env (防止系统默认设置)
        monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR, raising=False)

        gwt.when("调 clear_halt(admin_token='any-token')")
        cleared = guard.clear_halt(admin_token="any-token")

        gwt.then("clear_halt 返 False · 防测试污染生产")
        assert cleared is False
        assert guard.is_halted() is True

        gwt.when("即使 token 是空字符串 · 也拒")
        cleared_empty = guard.clear_halt(admin_token="")
        assert cleared_empty is False
