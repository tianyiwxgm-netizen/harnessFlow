"""Scenario 09 · T1-T3 · 3 project 同启 + IC 隔离 + audit 独立.

T1: 3 pid 同启 · 各 manager 独立
T2: IC-09 各分片独立 · pidA 事件不到 pidB/pidC
T3: audit 独立 · 各 pid hash chain 独立
"""
from __future__ import annotations

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
)


def test_t1_three_projects_concurrent_start(
    pid_a, pid_b, pid_c, topo_factory, make_wp_for, gwt: GWT
) -> None:
    """T1 · 3 pid 同启 · 各 WBSTopologyManager 干净独立."""
    with gwt("T1 · 3 pid 同启"):
        gwt.given("3 pid 各自 fresh · 互无关联")
        ma = topo_factory(pid_a)
        mb = topo_factory(pid_b)
        mc = topo_factory(pid_c)

        gwt.when("各装 1 个 WP · 不同 wp_id 不同 pid")
        ma.load_topology([make_wp_for(pid_a, "wp-a-1")], [])
        mb.load_topology([make_wp_for(pid_b, "wp-b-1")], [])
        mc.load_topology([make_wp_for(pid_c, "wp-c-1")], [])

        gwt.then("3 manager 各自 wp_states 含自己 WP · 不串")
        snap_a = ma.read_snapshot()
        snap_b = mb.read_snapshot()
        snap_c = mc.read_snapshot()
        assert "wp-a-1" in snap_a.wp_states
        assert "wp-b-1" in snap_b.wp_states
        assert "wp-c-1" in snap_c.wp_states
        assert "wp-b-1" not in snap_a.wp_states
        assert "wp-a-1" not in snap_b.wp_states


def test_t2_ic09_shards_isolated(
    pid_a, pid_b, pid_c, real_event_bus: EventBus, event_bus_root,
    emit_for, gwt: GWT,
) -> None:
    """T2 · IC-09 各分片独立 · pidA 的事件不到 pidB/pidC 分片."""
    with gwt("T2 · IC-09 PM-14 分片隔离"):
        gwt.given("3 pid 各 emit 1 条独立事件")
        emit_for(pid_a, "L1-03:wp_status_change", {"wp_id": "wp-a-1"})
        emit_for(pid_b, "L1-03:wp_status_change", {"wp_id": "wp-b-1"})
        emit_for(pid_c, "L1-03:wp_status_change", {"wp_id": "wp-c-1"})

        gwt.then("各 pid 分片各 1 条 · 自己分片有自己 wp_id")
        for pid, expected_wp in [
            (pid_a, "wp-a-1"),
            (pid_b, "wp-b-1"),
            (pid_c, "wp-c-1"),
        ]:
            evts = assert_ic_09_emitted(
                event_bus_root,
                project_id=pid,
                event_type="L1-03:wp_status_change",
                payload_contains={"wp_id": expected_wp},
            )
            assert len(evts) == 1


def test_t3_audit_chain_per_pid_independent(
    pid_a, pid_b, pid_c, real_event_bus: EventBus, event_bus_root,
    emit_for, gwt: GWT,
) -> None:
    """T3 · 各 pid hash chain 独立 · seq 各起从 1."""
    with gwt("T3 · audit chain 各 pid 独立"):
        gwt.given("3 pid 各 emit 不同条数事件")
        for _ in range(3):
            emit_for(pid_a, "L1-03:wp_status_change", {"x": 1})
        for _ in range(2):
            emit_for(pid_b, "L1-03:wp_status_change", {"x": 1})
        for _ in range(1):
            emit_for(pid_c, "L1-03:wp_status_change", {"x": 1})

        gwt.then("pid_a chain seq=3 · pid_b seq=2 · pid_c seq=1 · 互不串")
        n_a = assert_ic_09_hash_chain_intact(event_bus_root, project_id=pid_a)
        n_b = assert_ic_09_hash_chain_intact(event_bus_root, project_id=pid_b)
        n_c = assert_ic_09_hash_chain_intact(event_bus_root, project_id=pid_c)
        assert n_a == 3
        assert n_b == 2
        assert n_c == 1
