"""Scenario 04 · T6-T8 · 局部 fail 不影响其他 + 资源限额 + audit 完整.

T6: 1 WP fail · 其他 4 WP 仍 RUNNING (隔离)
T7: 资源限额 · parallelism_limit=2 时 5 WP 排队 · 不超限
T8: 5 WP 并发 audit chain 完整 · 无 GAP
"""
from __future__ import annotations

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
)


def test_t6_partial_fail_does_not_affect_others(
    project_id: str,
    loaded_topo: WBSTopologyManager,
    gwt: GWT,
) -> None:
    """T6 · wp-1 FAILED · wp-2..5 仍 RUNNING (隔离)."""
    with gwt("T6 · 局部 fail 不影响其他 4 WP"):
        gwt.given("5 WP 全 RUNNING")
        for i in range(1, 6):
            loaded_topo.transition_state(f"wp-{i}", State.READY, State.RUNNING)

        gwt.when("wp-1 失败 RUNNING→FAILED")
        loaded_topo.transition_state("wp-1", State.RUNNING, State.FAILED)

        gwt.then("wp-2..5 仍 RUNNING · 仅 wp-1 FAILED · 无连锁")
        snap = loaded_topo.read_snapshot()
        assert snap.wp_states["wp-1"] == State.FAILED
        for i in range(2, 6):
            assert snap.wp_states[f"wp-{i}"] == State.RUNNING, (
                f"wp-{i} 应隔离不受 wp-1 fail 影响"
            )


def test_t7_resource_quota_limit_2_with_5_wps(
    project_id: str,
    make_wp,
    gwt: GWT,
) -> None:
    """T7 · parallelism_limit=2 · 5 WP 排队 · 同时只能 2 路."""
    with gwt("T7 · 资源限额 parallelism=2"):
        gwt.given("5 WP · parallelism_limit=2")
        manager = WBSTopologyManager(project_id=project_id, parallelism_limit=2)
        wps = [make_wp(f"wp-{i}") for i in range(1, 6)]
        manager.load_topology(wps, [])

        gwt.when("起 2 个 WP RUNNING (达上限)")
        manager.transition_state("wp-1", State.READY, State.RUNNING)
        manager.transition_state("wp-2", State.READY, State.RUNNING)

        gwt.then("第 3 个 WP 不能 RUNNING (限额满)")
        # parallelism_limit 强制 2 · 第 3 起会 ParallelismCapError
        from app.l1_03.common.errors import ParallelismCapError
        try:
            manager.transition_state("wp-3", State.READY, State.RUNNING)
            raise AssertionError("应抛 ParallelismCapError")
        except ParallelismCapError:
            pass

        gwt.then("wp-1 完成后 · wp-3 才能跑 (排队)")
        manager.transition_state("wp-1", State.RUNNING, State.DONE)
        manager.transition_state("wp-3", State.READY, State.RUNNING)

        snap = manager.read_snapshot()
        running = [w for w, s in snap.wp_states.items() if s == State.RUNNING]
        assert set(running) == {"wp-2", "wp-3"}


def test_t8_audit_chain_intact_under_5_concurrent(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_event,
    gwt: GWT,
) -> None:
    """T8 · 5 WP 并发 audit · hash chain 完整 · 无 GAP."""
    with gwt("T8 · 5 WP 并发 audit hash chain 完整"):
        gwt.given("5 WP 各 emit 4 条事件 (status_change×3 + verdict)")
        for i in range(1, 6):
            for to_state in ["READY", "RUNNING", "DONE"]:
                emit_event(
                    "L1-03:wp_status_change",
                    {"wp_id": f"wp-{i}", "to_state": to_state},
                )
            emit_event(
                "L1-04:verdict_decided",
                {"wp_id": f"wp-{i}", "verdict": "PASS"},
            )

        gwt.then("audit 共 20 条事件 · hash chain 完整")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 20

        gwt.then("5 WP 各 1 条 verdict_decided=PASS · 全 emit")
        verdicts = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:verdict_decided",
            payload_contains={"verdict": "PASS"},
            min_count=5,
        )
        assert len({v["payload"]["wp_id"] for v in verdicts}) == 5
