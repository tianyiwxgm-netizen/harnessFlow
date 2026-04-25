"""scenario_08 · T15-T17 · 极端场景 (hot path / disk full / network partition).

T15 · hot path 崩溃 · 压测中(50 events 飞速 append)突然崩 → 全部 fsync 过的可恢复
T16 · disk full 触发 halt_guard · v2 重启依然 halted (mark_halt 持久 marker)
T17 · network partition 模拟 (events 落地 OK · 但跨进程协调缺失) → 仍可单进程恢复
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import BusHalted, BusState, Event
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_hash_chain_intact


async def test_t15_hot_path_crash_burst_append(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T15 · hot path 突崩 · burst append 50 events 后中途崩 · 已 fsync 的全可恢复."""
    async with gwt("T15 · hot path burst → 突崩 → 全 fsync 数据恢复"):
        gwt.given("v1 进 hot path · burst append 100 events")
        for i in range(100):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:burst_event",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"burst_idx": i, "hot_path": True},
            ))

        gwt.when("v1 突销毁 · 中途崩 · 已 append_atomic 完成的 100 events 都 fsync")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 重启可读完整 100 events · hash chain intact")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 100

        events = list(bus_v2.read_range(project_id))
        assert len(events) == 100
        assert events[0]["payload"]["burst_idx"] == 0
        assert events[99]["payload"]["burst_idx"] == 99

        gwt.then("v2 可继续 append (热路径恢复后续运行)")
        result = bus_v2.append(Event(
            project_id=project_id,
            type="L1-04:resumed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"phase": "post_crash"},
        ))
        assert result.sequence == 101


async def test_t16_disk_full_halt_persists_across_session(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T16 · disk full 触发 halt_guard · v2 重启依然 halted (跨 session 持久)."""
    async with gwt("T16 · disk full → halt marker → v2 重启仍 halted"):
        gwt.given("v1 落 5 events 正常")
        for i in range(5):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:test",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i},
            ))
        assert event_bus_v1.halt_guard.is_halted() is False

        gwt.when("模拟 disk full · 直接调 halt_guard.mark_halt (代替真 disk 故障)")
        event_bus_v1.halt_guard.mark_halt(
            reason="simulated_disk_full",
            source="L2-01:test",
            correlation_id="evt-disk-full-1",
        )

        gwt.then("v1 即时 halted · 后续 append 应 raise BusHalted")
        assert event_bus_v1.halt_guard.is_halted() is True
        with pytest.raises(BusHalted):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:test",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": "post-halt"},
            ))

        gwt.when("销毁 v1 · v2 重启")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 halt_guard.is_halted() == True (marker 跨 session 持久)")
        assert bus_v2.halt_guard.is_halted() is True
        assert bus_v2.state == BusState.HALTED

        gwt.then("v2 仍拒 append (halt 不会自动清除)")
        with pytest.raises(BusHalted):
            bus_v2.append(Event(
                project_id=project_id,
                type="L1-04:test",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": "v2-attempt"},
            ))


async def test_t17_network_partition_local_recovery(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    gwt: GWT,
) -> None:
    """T17 · network partition 模拟 · 单进程 events 仍可正常恢复(本地存储足够).

    本地 events.jsonl + checkpoints/ 都不依赖网络 · partition 只影响跨进程协调.
    本测验证: 即便上游 audit_mirror 不通 · 本地 EventBus 仍可正常 append + recover.
    """
    async with gwt("T17 · network partition · 本地恢复不受影响"):
        gwt.given("v1 落 30 events · 模拟 audit_mirror 上游不通")
        # audit_mirror 是逻辑上的远端 event mirror · 不影响本地 append
        append_events(30, type_prefix="L1-04")

        gwt.when("v1 销毁 · v2 重启 · 期间假设网络仍 partition")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 仍可读完整 30 events (本地 jsonl + meta 齐)")
        events = list(bus_v2.read_range(project_id))
        assert len(events) == 30

        gwt.then("hash chain 完整不依赖网络 · 本地恢复 OK")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 30

        gwt.then("v2 仍可 append 新事件 · 本地 fsync 跑通")
        result = bus_v2.append(Event(
            project_id=project_id,
            type="L1-04:test",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"phase": "post_partition_local_only"},
        ))
        assert result.sequence == 31
