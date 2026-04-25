"""Scenario 06 · T19-T20 · panic 期间用户告警 (UI 红屏 · IC-19 强通知).

panic 触发后 · UI 层应:
- T19 panic_history 留痕 · UI 可读 (含 reason / scope / latency_ms / was_halted)
- T20 IC-19 强通知接口 · UI 通过 panic_handler 公开 API 拉到 panic 状态

注:本 WP 不直接接 UI · 只验证 panic_handler 的公开状态可被 UI 层抓.
"""
from __future__ import annotations

import pytest

from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T19 · panic_history 完整留痕 · UI 红屏可读 reason/scope/latency
# ============================================================================


def test_t19_panic_history_provides_ui_red_card_data(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T19 · panic_history 留痕 · UI 红屏可读 reason / latency_ms / scope."""
    with gwt("T19 · panic 后 history 提供 UI 红屏 payload"):
        gwt.given("3 次连续 panic (干净 enforcer 各一次)")
        # 一次性 PAUSED 后再 panic 会 ALREADY_PAUSED · 所以只测 1 次
        gwt.when("发 1 条 user-triggered panic (含 user_id + reason)")
        signal = make_panic_signal(
            panic_id="panic-t19-ui-alert",
            user_id="user-alice-2026",
            reason="hash chain at seq=1234 broken; halting all ticks",
            scope="session",
        )
        result = panic_handler.handle(signal)

        gwt.then("history 提供 UI 红屏需要的所有字段")
        h = panic_handler.panic_history
        assert len(h) == 1
        rec = h[0]

        # UI 红屏卡片必需字段 (IC-19 strong notify schema 简化版)
        ui_card_fields = {
            "panic_id": "panic-t19-ui-alert",
            "user_id": "user-alice-2026",
            "reason": "hash chain at seq=1234 broken; halting all ticks",
            "scope": "session",
        }
        for k, v in ui_card_fields.items():
            assert rec[k] == v, f"UI 卡片字段缺失/错 {k}={rec.get(k)} 应={v}"

        # 时间字段必带 (UI 显示 "panic 发生于...")
        assert "ts_ns" in rec
        assert isinstance(rec["ts_ns"], int)
        assert rec["ts_ns"] > 0

        # latency 字段供 UI 显 SLO 实测值
        assert "latency_ms" in rec
        assert rec["latency_ms"] >= 0

        # was_halted 字段供 UI 区分 PAUSED vs HALTED 红屏
        assert "was_halted" in rec
        assert rec["was_halted"] is False  # 初始 RUNNING · 没 halt 过

        # slo_violated 供 UI 标红 (违反时显式告警)
        assert "slo_violated" in rec
        assert rec["slo_violated"] is False  # 应在 100ms 内


# ============================================================================
# T20 · IC-19 强通知:UI 通过公开 API (active_panic_id / state) 实时拉
# ============================================================================


def test_t20_ic19_strong_notify_api_for_ui(
    panic_handler: PanicHandler,
    halt_enforcer: HaltEnforcer,
    make_panic_signal,
    gwt: GWT,
) -> None:
    """T20 · UI 实时 polling 公开 API · 看到 panic 触发立即转红屏状态."""
    with gwt("T20 · IC-19 UI polling · panic 触发后立即可见状态"):
        gwt.given("UI 启动 polling · 初始 enforcer RUNNING · 无 active panic")
        # 模拟 UI 第一次 poll
        snapshot_before = {
            "tick_state": halt_enforcer.as_tick_state().value,
            "active_panic_id": panic_handler.active_panic_id,
            "active_user_id": panic_handler.active_user_id,
            "history_count": len(panic_handler.panic_history),
        }
        assert snapshot_before["tick_state"] == "RUNNING"
        assert snapshot_before["active_panic_id"] is None
        assert snapshot_before["history_count"] == 0

        gwt.when("用户点 panic 按钮 → handler.handle 同步落定")
        signal = make_panic_signal(
            panic_id="panic-t20-strong-notify",
            user_id="user-bob-emergency",
            reason="emergency stop requested by user",
        )
        panic_handler.handle(signal)

        gwt.then("UI 下一轮 poll 立即看到红屏 state · panic_id · user_id")
        snapshot_after = {
            "tick_state": halt_enforcer.as_tick_state().value,
            "active_panic_id": panic_handler.active_panic_id,
            "active_user_id": panic_handler.active_user_id,
            "history_count": len(panic_handler.panic_history),
        }
        assert snapshot_after["tick_state"] == "PAUSED"  # UI 转红屏触发条件
        assert snapshot_after["active_panic_id"] == "panic-t20-strong-notify"
        assert snapshot_after["active_user_id"] == "user-bob-emergency"
        assert snapshot_after["history_count"] == 1

        gwt.then("snapshot 字段对 UI 是 read-only · 多次拉取稳定不变")
        for _ in range(20):
            now = {
                "tick_state": halt_enforcer.as_tick_state().value,
                "active_panic_id": panic_handler.active_panic_id,
            }
            assert now == {
                "tick_state": "PAUSED",
                "active_panic_id": "panic-t20-strong-notify",
            }
