"""Scenario 09 · T7-T10 · 一个崩溃不影响其他 + panic 仅本 pid + SLO + 退出独立.

T7: 1 pid 崩溃 (异常) 不影响其他 2 pid
T8: panic 仅本 pid · pidA panic 不传 pidB/C
T9: SLO 各自满足 (3 pid 同启 < 100ms)
T10: 退出独立 · pidA 关闭不影响 pidB/C
"""
from __future__ import annotations

import time

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import PanicHandler, PanicSignal
from app.main_loop.tick_scheduler.schemas import TickState
from datetime import UTC, datetime
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
)


def test_t7_one_pid_crash_does_not_affect_others(
    pid_a, pid_b, pid_c, topo_factory, make_wp_for, gwt: GWT
) -> None:
    """T7 · pidA manager 崩溃 (raise exc) 不影响 pidB/C."""
    with gwt("T7 · 一 pid 崩溃 · 其他不受影响"):
        gwt.given("3 pid 各 1 RUNNING WP")
        ma = topo_factory(pid_a, parallelism=2)
        mb = topo_factory(pid_b, parallelism=2)
        mc = topo_factory(pid_c, parallelism=2)
        for m, pid in [(ma, pid_a), (mb, pid_b), (mc, pid_c)]:
            m.load_topology([make_wp_for(pid, f"wp-{pid[-1]}-1")], [])
            m.transition_state(f"wp-{pid[-1]}-1", State.READY, State.RUNNING)

        gwt.when("pidA manager 触发非法 transition (raise IllegalTransition)")
        from app.l1_03.common.errors import IllegalTransition
        try:
            ma.transition_state("wp-a-1", State.READY, State.DONE)  # 非法
        except IllegalTransition:
            pass

        gwt.then("pidB · pidC manager 仍正常 · 不受 pidA 异常影响")
        snap_b = mb.read_snapshot()
        snap_c = mc.read_snapshot()
        assert snap_b.wp_states["wp-b-1"] == State.RUNNING
        assert snap_c.wp_states["wp-c-1"] == State.RUNNING


def test_t8_panic_only_affects_own_pid(
    pid_a, pid_b, pid_c, real_event_bus: EventBus, event_bus_root,
    emit_for, gwt: GWT,
) -> None:
    """T8 · panic 仅本 pid · pidA panic 时 · pidB/C 不感知."""
    with gwt("T8 · panic 仅本 pid 不传染"):
        # PanicHandler scope 必须 pid- 前缀 (^pid-[A-Za-z0-9_-]{3,}$)
        # 我们用纯 IC 测试角度: pidA 写 panic event · pidB/C 不感知
        gwt.given("pidA emit panic event")
        # Note: PanicHandler 用 pid- 前缀 (与 PM-14 ^[a-z0-9_-]{1,40}$ 不同)
        # 我们用 audit emit 模拟 panic 事件
        emit_for(
            pid_a,
            "L1-01:panic_received",
            {"panic_id": "panic-pid-a-only", "scope": "tick"},
        )

        gwt.then("pidA 分片 1 panic event · pidB/C 0 panic event")
        events_a = assert_ic_09_emitted(
            event_bus_root,
            project_id=pid_a,
            event_type="L1-01:panic_received",
        )
        assert len(events_a) == 1

        gwt.then("pidB · pidC 分片无任何事件")
        assert_no_events_for_pid(event_bus_root, project_id=pid_b)
        assert_no_events_for_pid(event_bus_root, project_id=pid_c)


def test_t9_slo_three_pids_concurrent_under_100ms(
    pid_a, pid_b, pid_c, topo_factory, make_wp_for, gwt: GWT
) -> None:
    """T9 · 3 pid 各 1 WP 起 RUNNING · 端到端 < 100ms."""
    with gwt("T9 · 3 pid SLO < 100ms"):
        gwt.given("3 fresh manager")
        ma = topo_factory(pid_a)
        mb = topo_factory(pid_b)
        mc = topo_factory(pid_c)
        for m, pid in [(ma, pid_a), (mb, pid_b), (mc, pid_c)]:
            m.load_topology([make_wp_for(pid, f"wp-{pid[-1]}-1")], [])

        gwt.when("3 pid 串行 transition · 测端到端")
        t0 = time.monotonic()
        for m, pid in [(ma, pid_a), (mb, pid_b), (mc, pid_c)]:
            m.transition_state(f"wp-{pid[-1]}-1", State.READY, State.RUNNING)
        elapsed_ms = (time.monotonic() - t0) * 1000

        gwt.then(f"3 pid SLO < 100ms · 实际 {elapsed_ms:.2f}ms")
        assert elapsed_ms < 100.0


def test_t10_exit_one_pid_does_not_affect_others(
    pid_a, pid_b, pid_c, real_event_bus: EventBus, event_bus_root,
    emit_for, gwt: GWT,
) -> None:
    """T10 · pidA 退出 (写 closed event) 不影响 pidB/C."""
    with gwt("T10 · 退出独立 · 不传染"):
        gwt.given("3 pid 各 emit 1 condition · 共 3 条 audit")
        emit_for(pid_a, "L1-02:gate_decision", {"stage": "S6", "decision": "pass"})
        emit_for(pid_b, "L1-02:gate_decision", {"stage": "S4", "decision": "pass"})
        emit_for(pid_c, "L1-02:gate_decision", {"stage": "S2", "decision": "pass"})

        gwt.when("pidA 退出 · emit project_closed audit")
        emit_for(pid_a, "L1-02:project_closed", {"reason": "delivery_done"})

        gwt.then("pidA 含 closed event · pidB/C 不含")
        a_closed = assert_ic_09_emitted(
            event_bus_root,
            project_id=pid_a,
            event_type="L1-02:project_closed",
        )
        assert len(a_closed) == 1

        gwt.then("pidB · pidC 仍只有 gate_decision · 各 1 条")
        n_b = assert_ic_09_hash_chain_intact(event_bus_root, project_id=pid_b)
        n_c = assert_ic_09_hash_chain_intact(event_bus_root, project_id=pid_c)
        assert n_b == 1
        assert n_c == 1
