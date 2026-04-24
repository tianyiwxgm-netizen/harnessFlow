"""Smoke: IC-06 KB read / IC-15 halt / IC-17 panic-100ms 断言."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_15_halt_emitted,
    assert_kb_read_degraded,
    assert_kb_read_returned,
    assert_panic_within_100ms,
)


# --------- IC-06 KB ---------


@dataclass
class _FakeEntry:
    id: str
    kind: str = "pattern"


@dataclass
class _FakeMeta:
    project_id: str
    degraded: bool = False
    fallback_reason: str | None = None


@dataclass
class _FakeReadResult:
    entries: list = field(default_factory=list)
    meta: _FakeMeta = None  # type: ignore[assignment]


def test_assert_kb_read_returned_success() -> None:
    res = _FakeReadResult(
        entries=[_FakeEntry("e-1", "pattern"), _FakeEntry("e-2", "gotcha")],
        meta=_FakeMeta(project_id="proj-x"),
    )
    matched = assert_kb_read_returned(
        res, project_id="proj-x", min_entries=2, must_contain_kind="gotcha",
        must_contain_id="e-1",
    )
    assert len(matched) == 2


def test_assert_kb_read_returned_pm14_violation() -> None:
    res = _FakeReadResult(entries=[_FakeEntry("e-1")], meta=_FakeMeta(project_id="proj-other"))
    with pytest.raises(AssertionError, match="PM-14 违反"):
        assert_kb_read_returned(res, project_id="proj-x")


def test_assert_kb_read_degraded() -> None:
    res = _FakeReadResult(
        entries=[_FakeEntry("e-1")],
        meta=_FakeMeta(project_id="p", degraded=True, fallback_reason="rerank_timeout"),
    )
    assert_kb_read_degraded(res, expected=True, reason_contains="rerank")
    with pytest.raises(AssertionError):
        assert_kb_read_degraded(res, expected=False)


# --------- IC-15 halt ---------


def test_assert_ic_15_halt_emitted(real_event_bus: EventBus, event_bus_root) -> None:
    real_event_bus.append(Event(
        project_id="system",
        type="L1-09:bus_halted",
        actor="audit_mirror",
        payload={"reason": "fsync_failed"},
        timestamp=datetime.now(UTC),
    ))
    evt = assert_ic_15_halt_emitted(event_bus_root, reason_contains="fsync")
    assert evt["payload"]["reason"] == "fsync_failed"


def test_assert_ic_15_halt_not_emitted_fails(event_bus_root) -> None:
    with pytest.raises(AssertionError, match="bus_halted 未 emit"):
        assert_ic_15_halt_emitted(event_bus_root)


# --------- IC-17 panic ---------


def test_assert_panic_within_100ms_ok() -> None:
    t0 = time.monotonic()
    t1 = t0 + 0.05  # 50 ms
    elapsed = assert_panic_within_100ms(t0, t1, budget_ms=100.0)
    assert 40 <= elapsed <= 60


def test_assert_panic_within_100ms_fails_on_overbudget() -> None:
    t0 = time.monotonic()
    t1 = t0 + 0.2  # 200 ms
    with pytest.raises(AssertionError, match="panic 超时"):
        assert_panic_within_100ms(t0, t1, budget_ms=100.0)
