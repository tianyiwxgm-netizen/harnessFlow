"""ε-WP06 · PM-14 跨 project 硬约束测试。"""

from __future__ import annotations

import pytest

from app.l1_03.common.errors import PM14MismatchError
from app.l1_03.common.event_bus_stub import EventBusStub
from app.l1_03.scheduler import GetNextWPQuery, WPDispatcher
from app.l1_03.topology.manager import WBSTopologyManager


def test_pm14_load_topology_rejects_cross_project_wp(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> None:
    """WP.project_id != manager.project_id → PM14MismatchError。"""
    manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    bad_wp = make_wp("wp-x", proj="pid-OTHER")
    with pytest.raises(PM14MismatchError):
        manager.load_topology([bad_wp], [])


def test_pm14_dispatcher_rejects_cross_project_query(
    project_id: str, event_bus: EventBusStub, make_wp,
) -> None:
    """query.project_id != manager.project_id → E_WP_CROSS_PROJECT。"""
    manager = WBSTopologyManager(project_id=project_id, event_bus=event_bus)
    manager.load_topology([make_wp("wp-a")], [])
    d = WPDispatcher(manager, event_bus)
    q = GetNextWPQuery(query_id="q", project_id="pid-DIFFERENT", requester_tick="t")
    r = d.get_next_wp(q)
    assert r.error_code == "E_WP_CROSS_PROJECT"
    assert r.wp_id is None


def test_pm14_event_bus_rejects_empty_project_id() -> None:
    """IC-09 append_event 必带 project_id（PM-14 根字段）。"""
    bus = EventBusStub()
    with pytest.raises(ValueError, match="PM-14"):
        bus.append(event_type="x", content={}, project_id="")
