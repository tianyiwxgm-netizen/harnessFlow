"""EventBusStub + L1-02/03/04 stubs 的契约测试。

stub 是 L2-01 采集器唯一对外依赖入口 · 契约绿是 downstream TDD 前置。
"""
from __future__ import annotations

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.common.ids import ProjectId


pytestmark = pytest.mark.asyncio


async def test_append_and_read_single_event(pid: ProjectId) -> None:
    bus = EventBusStub()
    await bus.append_event(
        project_id=pid.value,
        type="L1-07:snapshot_captured",
        payload={"snapshot_id": "snap-1", "degradation_level": "FULL"},
    )
    events = await bus.read_event_stream(
        project_id=pid.value,
        types=["L1-07:snapshot_captured"],
        window_sec=60,
    )
    assert len(events) == 1
    assert events[0].type == "L1-07:snapshot_captured"
    assert events[0].project_id == pid.value


async def test_read_event_stream_filters_by_type(pid: ProjectId) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="decision", payload={"a": 1})
    await bus.append_event(project_id=pid.value, type="tool_invoked", payload={"tool": "git"})
    filtered = await bus.read_event_stream(
        project_id=pid.value, types=["tool_invoked"], window_sec=60
    )
    assert [e.type for e in filtered] == ["tool_invoked"]


async def test_read_event_stream_no_filter_returns_all(pid: ProjectId) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="a", payload={})
    await bus.append_event(project_id=pid.value, type="b", payload={})
    evs = await bus.read_event_stream(project_id=pid.value, types=None, window_sec=60)
    assert {e.type for e in evs} == {"a", "b"}


async def test_read_event_stream_isolates_project(pid: ProjectId) -> None:
    bus = EventBusStub()
    other = ProjectId.generate()
    await bus.append_event(project_id=pid.value, type="x", payload={})
    await bus.append_event(project_id=other.value, type="x", payload={})
    evs = await bus.read_event_stream(project_id=pid.value, types=["x"], window_sec=60)
    assert len(evs) == 1
    assert evs[0].project_id == pid.value


async def test_append_enforces_pid_pm14() -> None:
    bus = EventBusStub()
    with pytest.raises(ValueError, match="project_id"):
        await bus.append_event(project_id="", type="x", payload={})


async def test_read_event_bus_stats_returns_count_and_lag(pid: ProjectId) -> None:
    bus = EventBusStub()
    for i in range(3):
        await bus.append_event(project_id=pid.value, type="tick", payload={"i": i})
    stats = await bus.read_event_bus_stats(project_id=pid.value, window_sec=30)
    assert stats["event_count_last_30s"] == 3
    assert "event_lag_ms" in stats
    assert "tick" in stats["event_types"]


async def test_append_returns_event_id(pid: ProjectId) -> None:
    bus = EventBusStub()
    ev_id = await bus.append_event(project_id=pid.value, type="t", payload={})
    assert ev_id.startswith("ev-")


async def test_l102_stub_default_returns_s3(pid: ProjectId) -> None:
    s = L102Stub()
    lifecycle = await s.read_lifecycle_state(pid.value)
    assert lifecycle["phase"] == "S3"
    artifacts = await s.read_stage_artifacts(pid.value)
    assert artifacts["completeness_pct"] == 75.0


async def test_l102_stub_timeout_raises(pid: ProjectId) -> None:
    s = L102Stub(_timeout=True)
    with pytest.raises(TimeoutError):
        await s.read_lifecycle_state(pid.value)
    with pytest.raises(TimeoutError):
        await s.read_stage_artifacts(pid.value)


async def test_l102_stub_unavailable_raises(pid: ProjectId) -> None:
    s = L102Stub(_unavailable=True)
    with pytest.raises(RuntimeError):
        await s.read_lifecycle_state(pid.value)


async def test_l103_stub_wbs_snapshot(pid: ProjectId) -> None:
    s = L103Stub(total=20, completed=5, in_progress=3, blocked=1)
    snap = await s.read_wbs_snapshot(pid.value)
    assert snap["total"] == 20
    assert snap["completion_pct"] == 25.0


async def test_l104_stub_self_repair_rate(pid: ProjectId) -> None:
    s = L104Stub(attempts=10, successes=7, failures=3)
    stats = await s.read_self_repair_stats(pid.value)
    assert stats["rate"] == 0.7


async def test_l104_stub_rollback_counter(pid: ProjectId) -> None:
    s = L104Stub(rollback_count=4, rollback_reasons={"L2_verdict": 3, "L3_verdict": 1})
    rc = await s.read_rollback_counter(pid.value)
    assert rc["count"] == 4
    assert rc["by_reason"]["L2_verdict"] == 3
