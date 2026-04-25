"""IC-02 × IC-09 mini e2e · 跨 IC 跨链 · 2 TC.

覆盖:
- TC-1 · 完整 WP 生命周期(READY → RUNNING → DONE) · 落 2 条 wp_state_changed +
        wbs_decomposed · IC-09 hash chain 完整
- TC-2 · 跨 pid 隔离 · 2 manager 同时跑 · 各自 events.jsonl 独立 · 不混分片
"""
from __future__ import annotations

from pathlib import Path

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import DAGEdge
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
)
from tests.integration.ic_02.conftest import L103ToL109Bridge


def test_wp_lifecycle_chain_intact(
    manager: WBSTopologyManager,
    linear_wbs,
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
) -> None:
    """完整生命周期 · 装图 + 2 跃迁 · IC-09 hash chain 全程不断."""
    wps, edges = linear_wbs
    manager.load_topology(wps, edges)
    manager.transition_state("wp-001", State.READY, State.RUNNING)
    manager.transition_state("wp-001", State.RUNNING, State.DONE)

    # wbs_decomposed (1) + 2 wp_state_changed = 3 events
    total = assert_ic_09_hash_chain_intact(
        event_bus_root, project_id=project_id,
    )
    assert total >= 3, f"期望 ≥ 3 条 · 实际 {total}"

    # 类型分布
    decomposed = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-03:wbs_decomposed", min_count=1,
    )
    state_changed = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-03:wp_state_changed", min_count=2,
    )
    assert len(decomposed) == 1
    assert len(state_changed) == 2


def test_cross_pid_isolation(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    other_project_id: str,
    make_wp,
) -> None:
    """两个 manager 跑两个 pid · 各自 events.jsonl 独立 · 不混分片."""
    bridge = L103ToL109Bridge(real_event_bus)

    # 项目 A
    wp_a = make_wp("wp-a-001", proj=project_id)
    mgr_a = WBSTopologyManager(project_id=project_id, event_bus=bridge)
    mgr_a.load_topology([wp_a])
    mgr_a.transition_state("wp-a-001", State.READY, State.RUNNING)

    # 校验项目 A 有事件 · B 无事件
    assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-03:wp_state_changed", min_count=1,
        payload_contains={"wp_id": "wp-a-001"},
    )
    assert_no_events_for_pid(event_bus_root, project_id=other_project_id)

    # 项目 B 启动
    wp_b = make_wp("wp-b-001", proj=other_project_id)
    mgr_b = WBSTopologyManager(project_id=other_project_id, event_bus=bridge)
    mgr_b.load_topology([wp_b])
    mgr_b.transition_state("wp-b-001", State.READY, State.RUNNING)

    # 各自分片正确
    a_evts = assert_ic_09_emitted(
        event_bus_root, project_id=project_id,
        event_type="L1-03:wp_state_changed", min_count=1,
    )
    b_evts = assert_ic_09_emitted(
        event_bus_root, project_id=other_project_id,
        event_type="L1-03:wp_state_changed", min_count=1,
    )
    # A 分片不含 B 的 wp_id
    a_wp_ids = {e["payload"]["wp_id"] for e in a_evts}
    b_wp_ids = {e["payload"]["wp_id"] for e in b_evts}
    assert "wp-b-001" not in a_wp_ids
    assert "wp-a-001" not in b_wp_ids
