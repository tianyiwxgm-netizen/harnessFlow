"""scenario_08 · T9-T11 · 幂等保护 (重启后重复调用不重 emit).

T9 · IC-09 同 idempotency_key append 重复 → 第二次返 idempotent_replay=True
T10 · IC-09 同 event_id 重复 append → 同上幂等
T11 · 跨 session: v2 重 append 同 event_id (同进程内 cache) 仍幂等
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_hash_chain_intact


async def test_t9_idempotency_key_dedup(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    gwt: GWT,
) -> None:
    """T9 · idempotency_key 同值两次 append · 第二次返 idempotent_replay=True."""
    async with gwt("T9 · idempotency_key 幂等去重"):
        gwt.given("v1 · 第一次 append idempotency_key='task-1-finished'")
        evt1 = Event(
            project_id=project_id,
            type="L1-04:wp_completed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"wp_id": "wp-1"},
            idempotency_key="task-1-finished",
        )
        result1 = event_bus_v1.append(evt1)
        assert result1.idempotent_replay is False
        assert result1.sequence == 1

        gwt.when("第二次 append 相同 idempotency_key (同 payload)")
        evt2 = Event(
            project_id=project_id,
            type="L1-04:wp_completed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"wp_id": "wp-1"},
            idempotency_key="task-1-finished",
        )
        result2 = event_bus_v1.append(evt2)

        gwt.then("结果是 idempotent replay · sequence 不增")
        assert result2.idempotent_replay is True
        assert result2.event_id == result1.event_id
        assert result2.sequence == 1

        gwt.then("物理 events.jsonl 仍只有 1 条")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 1


async def test_t10_event_id_dedup(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    gwt: GWT,
) -> None:
    """T10 · 同 event_id 显式两次 append · 第二次幂等."""
    async with gwt("T10 · event_id 显式重复 幂等"):
        gwt.given("v1 · 第一次 append 显式 event_id")
        import ulid
        eid = f"evt_{ulid.new()}"
        evt1 = Event(
            project_id=project_id,
            type="L1-04:wp_completed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"wp_id": "wp-2"},
            event_id=eid,
        )
        r1 = event_bus_v1.append(evt1)
        assert r1.idempotent_replay is False
        assert r1.event_id == eid

        gwt.when("第二次 append · 同 event_id")
        evt2 = Event(
            project_id=project_id,
            type="L1-04:wp_completed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"wp_id": "wp-2-other"},
            event_id=eid,
        )
        r2 = event_bus_v1.append(evt2)

        gwt.then("idempotent_replay=True · 同 event_id")
        assert r2.idempotent_replay is True
        assert r2.event_id == eid

        gwt.then("物理只 1 条")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 1


async def test_t11_cross_session_idempotency_via_persistent_seq(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T11 · 跨 session 幂等 · seq 通过 meta.json 跨 session 持久(防重复 seq).

    注意:cache 是进程内 · 跨 session 缓存丢 · 但 sequence 通过 meta.json 持久 ·
    保证 v2 不会从 seq=1 重新开始.
    """
    async with gwt("T11 · 跨 session sequence 不重置"):
        gwt.given("v1 落 5 events · 末 seq=5")
        for i in range(5):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:test",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i},
            ))
        n_v1 = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_v1 == 5

        gwt.when("销毁 v1 · v2 重启 · append 1 条新事件")
        del event_bus_v1
        bus_v2 = restart_session()
        new_evt = Event(
            project_id=project_id,
            type="L1-04:test",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"phase": "v2"},
        )
        result = bus_v2.append(new_evt)

        gwt.then("v2 第一个新事件 seq=6 · 不重置到 1")
        assert result.sequence == 6

        gwt.then("hash chain 跨 session 仍连续 · 总 6 events")
        n_total = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_total == 6

        gwt.then("再追 1 条 · seq=7 (sequence 严格递增 跨 session)")
        result2 = bus_v2.append(Event(
            project_id=project_id,
            type="L1-04:test",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"phase": "v2-2"},
        ))
        assert result2.sequence == 7
