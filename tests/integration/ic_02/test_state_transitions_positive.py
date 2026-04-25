"""IC-02 · 5 正向 TC · WP 状态全转换 + IC-09 落盘.

每条合法跃迁验证:
1. transition_state 不抛
2. wp.state == new_state(读)
3. L1-03:wp_state_changed event 落到 events.jsonl(IC-09)
4. payload 含 wp_id / from_state / to_state / topology_version
5. PM-14 分片 · event 落到 projects/<pid>/events.jsonl
"""
from __future__ import annotations

from pathlib import Path

from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from tests.shared.ic_assertions import assert_ic_09_emitted


class TestIC02PositiveTransitions:
    """IC-02 · 5 条主要合法跃迁 · 每条 1 TC · 真 IC-09 落盘断言."""

    # ---- TC-1 · READY → RUNNING (锁定) ----
    def test_ready_to_running_emits_wp_state_changed(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        wp = manager.find_wp("wp-001")
        assert wp is not None
        assert wp.state == State.RUNNING

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_state_changed",
            min_count=1,
            payload_contains={"wp_id": "wp-001", "to_state": "RUNNING"},
        )
        assert events[0]["payload"]["from_state"] == "READY"
        assert "topology_version" in events[0]["payload"]

    # ---- TC-2 · RUNNING → DONE (wp_done) ----
    def test_running_to_done_emits_wp_state_changed(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state(
            "wp-001", State.RUNNING, State.DONE, reason="wp_done",
        )
        wp = manager.find_wp("wp-001")
        assert wp is not None
        assert wp.state == State.DONE

        # 仅取 to_state=DONE · 应有 1 条
        done_events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_state_changed",
            min_count=1,
            payload_contains={"wp_id": "wp-001", "to_state": "DONE"},
        )
        assert done_events[0]["payload"]["from_state"] == "RUNNING"
        assert done_events[0]["payload"]["reason"] == "wp_done"

    # ---- TC-3 · RUNNING → FAILED ----
    def test_running_to_failed_emits_wp_state_changed(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state(
            "wp-001", State.RUNNING, State.FAILED, reason="wp_failed",
        )
        wp = manager.find_wp("wp-001")
        assert wp is not None
        assert wp.state == State.FAILED

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_state_changed",
            min_count=1,
            payload_contains={"wp_id": "wp-001", "to_state": "FAILED"},
        )
        assert events[0]["payload"]["from_state"] == "RUNNING"
        assert events[0]["payload"]["reason"] == "wp_failed"

    # ---- TC-4 · FAILED → READY (放回重试) ----
    def test_failed_to_ready_emits_wp_state_changed(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state("wp-001", State.RUNNING, State.FAILED)
        manager.transition_state(
            "wp-001", State.FAILED, State.READY, reason="L2-05_retry",
        )
        wp = manager.find_wp("wp-001")
        assert wp is not None
        assert wp.state == State.READY

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_state_changed",
            min_count=1,
            payload_contains={"wp_id": "wp-001", "to_state": "READY"},
        )
        assert events[0]["payload"]["from_state"] == "FAILED"
        assert events[0]["payload"]["reason"] == "L2-05_retry"

    # ---- TC-5 · FAILED → STUCK (mark_stuck) ----
    def test_failed_to_stuck_emits_wp_state_changed(
        self,
        manager: WBSTopologyManager,
        linear_wbs,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        wps, edges = linear_wbs
        manager.load_topology(wps, edges)
        manager.transition_state("wp-001", State.READY, State.RUNNING)
        manager.transition_state("wp-001", State.RUNNING, State.FAILED)
        manager.mark_stuck("wp-001")
        wp = manager.find_wp("wp-001")
        assert wp is not None
        assert wp.state == State.STUCK

        events = assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-03:wp_state_changed",
            min_count=1,
            payload_contains={"wp_id": "wp-001", "to_state": "STUCK"},
        )
        assert events[0]["payload"]["from_state"] == "FAILED"
        assert events[0]["payload"]["reason"] == "stuck"
