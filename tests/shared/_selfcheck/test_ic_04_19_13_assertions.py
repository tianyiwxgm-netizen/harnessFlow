"""Smoke: IC-04 skill_invoke / IC-19 wbs dispatch / IC-13 supervisor sense."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_04_invoked,
    assert_ic_13_sense_emitted,
    assert_ic_19_wbs_accepted,
)


# --------- IC-04 skill_invoke ---------


def test_assert_ic_04_invoked_success() -> None:
    calls = [
        {"skill_id": "wbs-decomposer", "args": {"project_id": "proj-x"}},
        {"skill_id": "other", "args": {}},
    ]
    matched = assert_ic_04_invoked(calls, skill_id="wbs-decomposer", project_id="proj-x")
    assert len(matched) == 1


def test_assert_ic_04_invoked_fail_wrong_skill() -> None:
    with pytest.raises(AssertionError, match="skill_invoke 断言失败"):
        assert_ic_04_invoked([{"skill_id": "other", "args": {}}], skill_id="missing")


def test_assert_ic_04_invoked_fail_wrong_pid() -> None:
    calls = [{"skill_id": "s1", "args": {"project_id": "proj-a"}}]
    with pytest.raises(AssertionError):
        assert_ic_04_invoked(calls, skill_id="s1", project_id="proj-b")


# --------- IC-19 wbs ---------


def test_assert_ic_19_wbs_accepted_dict() -> None:
    res = {"status": "accepted", "project_id": "proj-x"}
    assert_ic_19_wbs_accepted(res, project_id="proj-x")


def test_assert_ic_19_wbs_rejected() -> None:
    with pytest.raises(AssertionError, match="accepted"):
        assert_ic_19_wbs_accepted({"status": "rejected", "project_id": "p"}, project_id="p")


def test_assert_ic_19_pm14_violation() -> None:
    res = {"status": "accepted", "project_id": "proj-other"}
    with pytest.raises(AssertionError, match="PM-14 违反"):
        assert_ic_19_wbs_accepted(res, project_id="proj-x")


# --------- IC-13 supervisor sense ---------


def test_assert_ic_13_sense_emitted(real_event_bus: EventBus, event_bus_root, project_id: str) -> None:
    real_event_bus.append(Event(
        project_id=project_id,
        type="L1-07:supervisor_sense_emitted",
        actor="supervisor",
        payload={"dim": "plan_drift", "magnitude": 0.3},
        timestamp=datetime.now(UTC),
    ))
    events = assert_ic_13_sense_emitted(event_bus_root, project_id=project_id, dim="plan_drift")
    assert len(events) == 1


def test_assert_ic_13_sense_not_emitted(event_bus_root, project_id: str) -> None:
    with pytest.raises(AssertionError, match="supervisor_sense_emitted 断言失败"):
        assert_ic_13_sense_emitted(event_bus_root, project_id=project_id)
