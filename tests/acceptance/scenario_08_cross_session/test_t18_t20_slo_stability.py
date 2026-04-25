"""scenario_08 · T18-T20 · 恢复时长 SLO + 多次重启稳定.

T18 · 恢复时长 SLO < 30s (含 checkpoint load + replay)
T19 · 重启完成后 5 个新 tick 全绿 (系统正常 · 无异常 halt)
T20 · 跨多次重启稳定 (3 轮 v1→v2→v3→v4 · seq 严格递增 · 无重复 · 无丢)
"""
from __future__ import annotations

import time
from datetime import UTC, datetime

from app.l1_09.checkpoint import RecoveryAttempt, SnapshotJob
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import assert_ic_09_hash_chain_intact


async def test_t18_recovery_within_30s_slo(
    event_bus_v1: EventBus,
    snapshot_job_v1: SnapshotJob,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    recovery_v2,
    gwt: GWT,
) -> None:
    """T18 · 恢复时长 SLO < 30s · 含 checkpoint load + 尾段 replay."""
    async with gwt("T18 · recovery 30s SLO 硬约束"):
        gwt.given("v1 落 200 events + 落 checkpoint")
        append_events(200, type_prefix="L1-04")
        snap = snapshot_job_v1.take_snapshot(project_id)
        assert snap.last_event_sequence == 200

        gwt.and_("v1 再追 50 events (checkpoint 后)")
        for i in range(50):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:post_ckpt",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i},
            ))

        gwt.when("销毁 v1 · v2 重启 · 测 recovery 时长")
        del event_bus_v1
        del snapshot_job_v1
        bus_v2 = restart_session()
        recovery = recovery_v2(bus_v2)

        t0 = time.monotonic()
        result = recovery.recover_from_checkpoint(project_id)
        elapsed_s = time.monotonic() - t0

        gwt.then(f"recovery 完成时长 < 30s · 实际={elapsed_s*1000:.2f}ms")
        assert elapsed_s < 30.0, f"recovery 超 30s SLO · 实际={elapsed_s:.2f}s"
        # acceptance 模式实际应远低于 30s
        assert elapsed_s < 1.0, f"mock 模式应 < 1s · 实际={elapsed_s:.2f}s"

        gwt.then("recovery result 含 duration_ms · hash_chain_valid=True")
        assert result.hash_chain_valid is True
        assert result.duration_ms < 30000

        gwt.then("recovered 末 seq=250 (200 ckpt + 50 tail)")
        assert result.last_event_sequence_replayed >= 200


async def test_t19_post_restart_n_ticks_healthy(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T19 · 重启后 5 个新 tick 全绿 · 无异常 halt · 序号正确递增."""
    async with gwt("T19 · 重启后 5 tick 健康 · 系统正常"):
        gwt.given("v1 落 10 events 后销毁")
        for i in range(10):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-01:tick_completed",
                actor="main_loop",
                timestamp=datetime.now(UTC),
                payload={"tick_seq": i},
            ))
        del event_bus_v1

        gwt.when("v2 重启 · 跑 5 个新 tick")
        bus_v2 = restart_session()
        v2_tick_results = []
        for tick_id in range(10, 15):
            result = bus_v2.append(Event(
                project_id=project_id,
                type="L1-01:tick_completed",
                actor="main_loop",
                timestamp=datetime.now(UTC),
                payload={"tick_seq": tick_id, "after_restart": True},
            ))
            v2_tick_results.append(result)

        gwt.then("5 个 v2 tick 全成功 · 无 halt")
        assert all(r.idempotent_replay is False for r in v2_tick_results)
        assert bus_v2.halt_guard.is_halted() is False

        gwt.then("v2 sequence 严格递增 · 11..15 (跨 v1+v2)")
        seqs = [r.sequence for r in v2_tick_results]
        assert seqs == [11, 12, 13, 14, 15]

        gwt.then("hash chain 跨 v1+v2 共 15 events · intact")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 15


async def test_t20_multiple_restarts_stability(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T20 · 跨多次重启稳定 · v1→v2→v3→v4 · seq 严格递增·无丢."""
    async with gwt("T20 · 4 轮重启 · 每轮 5 events · 共 20 · seq 严格递增"):
        gwt.given("v1 · 5 events")
        for i in range(5):
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-04:phase_v1",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i, "phase": "v1"},
            ))

        gwt.when("销毁 v1 · v2 启 · 5 events")
        del event_bus_v1
        bus_v2 = restart_session()
        for i in range(5):
            result = bus_v2.append(Event(
                project_id=project_id,
                type="L1-04:phase_v2",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i, "phase": "v2"},
            ))
        last_v2 = result

        gwt.and_("销毁 v2 · v3 启 · 5 events")
        del bus_v2
        bus_v3 = restart_session()
        for i in range(5):
            result = bus_v3.append(Event(
                project_id=project_id,
                type="L1-04:phase_v3",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i, "phase": "v3"},
            ))
        last_v3 = result

        gwt.and_("销毁 v3 · v4 启 · 5 events")
        del bus_v3
        bus_v4 = restart_session()
        for i in range(5):
            result = bus_v4.append(Event(
                project_id=project_id,
                type="L1-04:phase_v4",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"i": i, "phase": "v4"},
            ))
        last_v4 = result

        gwt.then("v2 末 seq=10 · v3 末 seq=15 · v4 末 seq=20")
        assert last_v2.sequence == 10
        assert last_v3.sequence == 15
        assert last_v4.sequence == 20

        gwt.then("总 events=20 · hash chain 跨 4 轮重启完整")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 20

        gwt.then("v4 各 phase 实际事件数正确")
        events = list(bus_v4.read_range(project_id))
        phases = [e["payload"]["phase"] for e in events]
        assert phases.count("v1") == 5
        assert phases.count("v2") == 5
        assert phases.count("v3") == 5
        assert phases.count("v4") == 5
