"""Scenario 06 · T10-T12 · 跨 session 持久 (重启仍 readonly · 直至运维清 panic 标志).

panic 触发后 → audit bus marker (HaltGuard) 跨进程持久 · 重启后仍 halted.
T10-T12 用 HaltGuard 模拟 cross-session panic 标志:

- T10 panic 后 marker 持久 · 新进程读到仍 halted
- T11 重启后系统进 readonly · 不接受新 append (BusHalted)
- T12 直到运维 admin_token 清 marker · 系统才能恢复
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.halt_guard import ADMIN_TOKEN_ENV_VAR, HaltGuard
from app.l1_09.event_bus.schemas import BusHalted, BusState, Event
from tests.shared.gwt_helpers import GWT


# ============================================================================
# T10 · panic 后 marker 跨 session 持久 (HaltGuard marker 文件)
# ============================================================================


def test_t10_panic_marker_persists_across_session(
    tmp_path: Path,
    gwt: GWT,
) -> None:
    """T10 · session A panic+marker · session B 起新 EventBus 仍 halted."""
    with gwt("T10 · panic 后 marker 跨 session 持久"):
        gwt.given("session A · 全新 bus + 触发 mark_halt (模拟 panic)")
        bus_root = tmp_path / "panic_persistent_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        bus_a.halt_guard.mark_halt(
            reason="panic: hash_chain_broken at seq=99",
            source="L2-01:panic_test",
            correlation_id="evt-test-t10",
        )
        assert bus_a.halt_guard.is_halted() is True
        assert bus_a.state == BusState.HALTED

        gwt.when("session A 关 · session B 起新 EventBus 同 bus_root")
        del bus_a
        bus_b = EventBus(bus_root)

        gwt.then("session B 自动 detect halt marker · state=HALTED")
        assert bus_b.halt_guard.is_halted() is True
        assert bus_b.state == BusState.HALTED

        gwt.then("marker 内容跨 session 完整 (reason / source / correlation_id)")
        info = bus_b.halt_guard.load_halt_info()
        assert info is not None
        assert "hash_chain_broken" in info.get("reason", "")
        assert info.get("source") == "L2-01:panic_test"
        assert info.get("correlation_id") == "evt-test-t10"


# ============================================================================
# T11 · 重启后系统进 readonly · 不接受新 append (BusHalted)
# ============================================================================


def test_t11_restart_into_readonly_rejects_appends(
    tmp_path: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T11 · session A panic · session B 起来 · 任何 append 抛 BusHalted."""
    with gwt("T11 · panic 重启后 · readonly 模式 · append 全拒"):
        gwt.given("session A · panic 触发 marker 落盘")
        bus_root = tmp_path / "readonly_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        bus_a.halt_guard.mark_halt(
            reason="panic readonly test", source="t11",
        )
        del bus_a

        gwt.when("session B 起 · 试 append")
        bus_b = EventBus(bus_root)
        evt = Event(
            project_id=project_id.replace("pid-", "p-"),  # bus pid 用 ^[a-z0-9_-]{1,40}$
            type="L1-01:tick_dispatched",
            actor="main_loop",
            timestamp=datetime.now(UTC),
            payload={"action": "noop"},
        )

        gwt.then("append 抛 BusHalted · 系统 readonly")
        with pytest.raises(BusHalted) as exc:
            bus_b.append(evt)
        assert "halt" in str(exc.value).lower() or "panic" in str(exc.value).lower()

        gwt.then("尝试多次 append · 仍全拒 (不绕过)")
        for _ in range(5):
            with pytest.raises(BusHalted):
                bus_b.append(evt)


# ============================================================================
# T12 · 运维 admin_token 清 marker · 系统恢复 RUNNING
# ============================================================================


def test_t12_ops_clears_panic_marker_via_admin_token(
    tmp_path: Path,
    monkeypatch,
    project_id: str,
    gwt: GWT,
) -> None:
    """T12 · 运维持 admin_token 清 panic marker · 重启后系统恢复."""
    with gwt("T12 · 运维 admin_token 清 marker · 系统恢复 RUNNING"):
        gwt.given("session A · panic 触发 marker 持久")
        bus_root = tmp_path / "ops_clear_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        bus_a.halt_guard.mark_halt(
            reason="panic to be cleared", source="t12",
        )
        assert bus_a.halt_guard.is_halted() is True

        gwt.when("运维设 HARNESS_ADMIN_TOKEN env + 调 clear_halt")
        monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "ops-recovery-token-2026")
        cleared = bus_a.halt_guard.clear_halt(admin_token="ops-recovery-token-2026")

        gwt.then("clear_halt 返 True · marker 删除")
        assert cleared is True
        assert bus_a.halt_guard.is_halted() is False

        gwt.when("起 session C 验证恢复 · append 成功")
        del bus_a
        bus_c = EventBus(bus_root)
        # bus_c.state 仍读 marker · 已清空 · 应 READY
        assert bus_c.halt_guard.is_halted() is False
        assert bus_c.state == BusState.READY

        evt = Event(
            project_id=project_id.replace("pid-", "p-"),
            type="L1-01:tick_dispatched",
            actor="main_loop",
            timestamp=datetime.now(UTC),
            payload={"action": "post_recovery"},
        )
        result = bus_c.append(evt)
        assert result.persisted is True
