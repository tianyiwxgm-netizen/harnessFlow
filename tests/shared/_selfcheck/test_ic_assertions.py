"""Smoke: ic_assertions 功能验证(IC-09 / IC-01 / PM-14)."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_events_only_for_pid,
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    assert_no_events_for_pid,
    assert_no_state_transition,
    assert_state_transition_to,
    list_events,
)


# --------- IC-09 emit ---------


def test_assert_ic_09_emitted_success(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-04:verifier_report_issued",
        actor="verifier",
        payload={"wp_id": "wp-1", "verdict": "PASS"},
        timestamp=datetime.now(UTC),
    ))
    matched = assert_ic_09_emitted(
        event_bus_root,
        project_id=project_id,
        event_type="L1-04:verifier_report_issued",
        payload_contains={"wp_id": "wp-1"},
        actor="verifier",
    )
    assert len(matched) == 1


def test_assert_ic_09_emitted_min_count_fail(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-04:rollback_executed",
        actor="verifier",
        payload={},
        timestamp=datetime.now(UTC),
    ))
    with pytest.raises(AssertionError, match="IC-09 事件断言失败"):
        assert_ic_09_emitted(
            event_bus_root,
            project_id=project_id,
            event_type="L1-04:rollback_executed",
            min_count=2,
        )


def test_assert_ic_09_hash_chain_intact(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    for i in range(3):
        real_event_bus.append(Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"i": i},
            timestamp=datetime.now(UTC),
        ))
    count = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
    assert count == 3


# --------- PM-14 isolation ---------


def test_assert_no_events_for_pid_empty(event_bus_root) -> None:
    assert_no_events_for_pid(event_bus_root, project_id="proj-never-used")


def test_assert_no_events_for_pid_violated(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-04:verifier_report_issued",
        actor="verifier",
        payload={},
        timestamp=datetime.now(UTC),
    ))
    with pytest.raises(AssertionError, match="PM-14 隔离违反"):
        assert_no_events_for_pid(event_bus_root, project_id=project_id)


def test_assert_events_only_for_pid(real_event_bus: EventBus, event_bus_root, project_id: str, other_project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-04:verifier_report_issued",
        actor="verifier",
        payload={},
        timestamp=datetime.now(UTC),
    ))
    # expected_pid 有 · other 无 · 断言通过
    assert_events_only_for_pid(
        event_bus_root,
        expected_pid=project_id,
        checked_pids=[project_id, other_project_id],
    )


def test_list_events_type_prefix(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id, type="L1-04:rollback_executed",
        actor="verifier", payload={}, timestamp=datetime.now(UTC),
    ))
    real_event_bus.append(Event(
        project_id=project_id, type="L1-09:bus_halted",
        actor="audit_mirror", payload={}, timestamp=datetime.now(UTC),
    ))
    l104 = list_events(event_bus_root, project_id, type_prefix="L1-04:")
    assert len(l104) == 1
    assert l104[0]["type"] == "L1-04:rollback_executed"


# --------- IC-01 state_transition ---------


def test_assert_state_transition_to_success() -> None:
    calls = [
        {"project_id": "proj-a", "wp_id": "wp-1", "new_wp_state": "retry_s3", "escalated": False, "route_id": "r-1"},
    ]
    matched = assert_state_transition_to(
        calls, wp_id="wp-1", new_wp_state="retry_s3", project_id="proj-a",
        escalated=False, route_id="r-1",
    )
    assert len(matched) == 1


def test_assert_state_transition_to_fail() -> None:
    with pytest.raises(AssertionError, match="IC-01 state_transition 断言失败"):
        assert_state_transition_to([], wp_id="wp-1", new_wp_state="retry_s3")


def test_assert_no_state_transition() -> None:
    assert_no_state_transition([])
    with pytest.raises(AssertionError):
        assert_no_state_transition([{"wp_id": "x", "new_wp_state": "y"}])
