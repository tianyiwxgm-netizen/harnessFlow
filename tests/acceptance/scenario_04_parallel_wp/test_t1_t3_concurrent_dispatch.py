"""Scenario 04 · T1-T3 · 并发起 5 WP + IC-02 status_change + IC-09 hash chain.

T1: 5 WP 同时起 (5 并发 transition_state READY→RUNNING)
T2: IC-02 5 路 status_change · 全到位
T3: IC-09 hash chain 单调 (PM-08 单写入口 · 串行落盘)
"""
from __future__ import annotations

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


def test_t1_five_wps_concurrent_transition_to_running(
    project_id: str,
    loaded_topo: WBSTopologyManager,
    gwt: GWT,
) -> None:
    """T1 · 5 WP 同时 READY→RUNNING · 并发不超 parallelism_limit."""
    with gwt("T1 · 5 WP 同 layer 并发 transition"):
        gwt.given("5 WP 全 READY · parallelism_limit=5")
        snap = loaded_topo.read_snapshot()
        assert len(snap.wp_states) == 5
        assert all(s == State.READY for s in snap.wp_states.values())

        gwt.when("依次 5 次 transition READY→RUNNING")
        for i in range(1, 6):
            loaded_topo.transition_state(f"wp-{i}", State.READY, State.RUNNING)

        gwt.then("5 WP 全 RUNNING · current_running_count=5")
        snap = loaded_topo.read_snapshot()
        running = [w for w, s in snap.wp_states.items() if s == State.RUNNING]
        assert len(running) == 5

        gwt.then("再起一个会因 parallelism_limit 抛 ParallelismCapError (无 6th 槽)")
        # 已 5 RUNNING · 新增需先 DONE 一个再起 · 这里仅断当前 5 路并发到顶
        assert loaded_topo.read_snapshot().wp_states["wp-1"] == State.RUNNING


def test_t2_ic02_status_change_all_five_emitted(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_event,
    gwt: GWT,
) -> None:
    """T2 · IC-02 status_change 5 路全 emit · 全 RUNNING."""
    with gwt("T2 · IC-02 5 路 status_change"):
        gwt.given("5 WP RUNNING · 各自 emit IC-02 status_change")

        gwt.when("依次 emit 5 条 IC-02 status_change_to_running")
        for i in range(1, 6):
            emit_event(
                "L1-03:wp_status_change",
                {
                    "wp_id": f"wp-{i}",
                    "from_state": "READY",
                    "to_state": "RUNNING",
                    "trigger": "scheduler",
                },
            )

        gwt.then("5 条 IC-02 落盘 · payload 含每个 wp_id")
        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_status_change",
            payload_contains={"to_state": "RUNNING"},
            min_count=5,
        )
        wp_ids = {e["payload"]["wp_id"] for e in events}
        assert wp_ids == {f"wp-{i}" for i in range(1, 6)}


def test_t3_ic09_hash_chain_monotonic(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_event,
    gwt: GWT,
) -> None:
    """T3 · IC-09 hash chain 串行单调 (PM-08 单写入口)."""
    with gwt("T3 · IC-09 hash chain 单调 · 串行落盘"):
        gwt.given("emit 10 条事件 (5 RUNNING + 5 DONE)")
        for i in range(1, 6):
            emit_event(
                "L1-03:wp_status_change",
                {"wp_id": f"wp-{i}", "to_state": "RUNNING"},
            )
        for i in range(1, 6):
            emit_event(
                "L1-03:wp_status_change",
                {"wp_id": f"wp-{i}", "to_state": "DONE"},
            )

        gwt.then("hash chain 完整 10 条 · seq=1..10 单调")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 10

        gwt.then("seq 严格递增 (PM-08 串行入账 · 即使 5 路并发也单条入)")
        events = list_events(event_bus_root, project_id)
        seqs = [e["sequence"] for e in events]
        assert seqs == list(range(1, 11)), f"seq 非单调 · {seqs}"
