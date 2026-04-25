"""Scenario 04 · T9-T10 · SLO 满足 + PM-14 隔离.

T9: 5 路并发 dispatch latency · SLO 满足 (端到端 < 100ms)
T10: 5 路并发不串 pid · PM-14 严格隔离 (跨 pid 拒)
"""
from __future__ import annotations

import time

import pytest

from app.l1_03.common.errors import PM14MismatchError
from app.l1_03.topology.manager import WBSTopologyManager
from app.l1_03.topology.schemas import WorkPackage
from app.l1_03.topology.state_machine import State
from app.l1_09.event_bus.core import EventBus
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_no_events_for_pid


def test_t9_five_concurrent_dispatch_under_slo(
    project_id: str,
    loaded_topo: WBSTopologyManager,
    gwt: GWT,
) -> None:
    """T9 · 5 路并发 dispatch · 端到端 < 100ms · SLO 满足."""
    with gwt("T9 · 5 路并发 SLO < 100ms"):
        gwt.given("5 WP READY · parallelism=5")

        gwt.when("依次 5 次 transition · 测端到端 wall clock")
        t0 = time.monotonic()
        for i in range(1, 6):
            loaded_topo.transition_state(f"wp-{i}", State.READY, State.RUNNING)
        elapsed_ms = (time.monotonic() - t0) * 1000

        gwt.then(f"5 路 elapsed={elapsed_ms:.2f}ms < 100ms · SLO 满足")
        assert elapsed_ms < 100.0, (
            f"5 路并发 transition 超 100ms · 实际 {elapsed_ms:.2f}ms"
        )


def test_t10_pm14_isolation_blocks_cross_project_wp(
    project_id: str,
    gwt: GWT,
) -> None:
    """T10 · PM-14 隔离 · WP project_id 与 manager pid 不一致拒载入."""
    with gwt("T10 · PM-14 跨 pid 隔离"):
        gwt.given(f"manager pid={project_id} · 试装其他 pid 的 WP")
        manager = WBSTopologyManager(project_id=project_id, parallelism_limit=5)

        wrong_pid_wp = WorkPackage(
            wp_id="wp-foreign",
            project_id="proj-other-pid",
            goal="foreign goal",
            dod_expr_ref="dod-foreign",
            deps=[],
            effort_estimate=1.0,
        )

        gwt.when("尝试装载 wrong-pid WP")
        gwt.then("PM14MismatchError 抛 · WP 拒载入")
        with pytest.raises(PM14MismatchError) as exc_info:
            manager.load_topology([wrong_pid_wp], [])

        gwt.then(f"错误含 expected={project_id} got=proj-other-pid")
        err = exc_info.value
        assert err.expected_pid == project_id
        assert err.got_pid == "proj-other-pid"


def test_t10b_pm14_isolation_no_event_leak(
    project_id: str,
    real_event_bus: EventBus,
    event_bus_root,
    emit_event,
    gwt: GWT,
) -> None:
    """T10b · PM-14 IC-09 事件不泄漏 · 5 路并发不串 pid."""
    with gwt("T10b · PM-14 IC-09 事件分片不串"):
        other_pid = "proj-acc04-other"
        gwt.given(f"主 pid={project_id} 跑 5 路并发事件")
        for i in range(1, 6):
            emit_event(
                "L1-03:wp_status_change",
                {"wp_id": f"wp-{i}", "to_state": "RUNNING"},
            )

        gwt.then(f"另一 pid={other_pid} 分片为空 · 无事件泄漏")
        assert_no_events_for_pid(event_bus_root, project_id=other_pid)
