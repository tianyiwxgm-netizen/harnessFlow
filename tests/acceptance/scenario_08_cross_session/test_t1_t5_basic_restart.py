"""scenario_08 · T1-T5 · 重启基本恢复(stage / WP / KB / audit / locks 5 维度).

T1 · stage 状态恢复 (events.jsonl 末 seq + last_hash 跨 session 可读)
T2 · WP 状态恢复 (业务 payload 跨 session 可读)
T3 · KB 状态恢复 (kb_session events 跨 session 可读)
T4 · audit-ledger 跨 session 完整(hash chain)
T5 · halt_guard marker 不存在 = 无误 halt(确认 cleanrestart)
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.l1_09.checkpoint import RecoveryAttempt, SnapshotJob
from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_hash_chain_intact,
    list_events,
)


async def test_t1_stage_recovery_after_crash(
    event_bus_v1: EventBus,
    snapshot_job_v1: SnapshotJob,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    recovery_v2,
    gwt: GWT,
) -> None:
    """T1 · stage 状态恢复 · S4 进度跨 session 可读."""
    async with gwt("T1 · stage 状态跨 session 恢复"):
        gwt.given(f"v1 session · pid={project_id} · 已落 50 events(模拟 S4 进 in_progress)")
        n = append_events(50, payload_extra={"stage": "S4"})
        assert n == 50

        gwt.and_("触发 SnapshotJob · 落 checkpoint")
        snap = snapshot_job_v1.take_snapshot(project_id)
        assert snap.last_event_sequence == 50

        gwt.when("销毁 v1 EventBus(模拟崩溃)")
        del event_bus_v1
        del snapshot_job_v1

        gwt.and_("v2 session 重启 · 用同 bus_root 装新 EventBus + RecoveryAttempt")
        bus_v2 = restart_session()
        recovery = recovery_v2(bus_v2)

        gwt.when("调 recover_from_checkpoint · 把 checkpoint 状态回放")
        result = recovery.recover_from_checkpoint(project_id)

        gwt.then("recovered · last_event_sequence_replayed == checkpoint last_seq")
        assert result.project_id == project_id
        assert result.checkpoint_id_used == snap.checkpoint_id
        assert result.hash_chain_valid is True

        gwt.then("recovered_state 含 last_seq=50 · stage 进度信息可读")
        recovered_payload = result.recovered_state
        assert recovered_payload["last_event_sequence"] == 50
        assert recovered_payload["events_count"] == 50


async def test_t2_wp_state_recovery(
    event_bus_v1: EventBus,
    snapshot_job_v1: SnapshotJob,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T2 · WP 状态(in_progress / completed)跨 session 可读 · 不丢."""
    async with gwt("T2 · WP4-5 in_progress 跨 session 不丢"):
        gwt.given("v1 session · 5 个 WP · WP1-3=completed · WP4-5=in_progress")
        for wp_id, status in [
            ("wp-1", "completed"),
            ("wp-2", "completed"),
            ("wp-3", "completed"),
            ("wp-4", "in_progress"),
            ("wp-5", "in_progress"),
        ]:
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-03:wp_state_changed",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"wp_id": wp_id, "status": status},
            ))

        gwt.and_("snapshot 落 ckpt")
        snap = snapshot_job_v1.take_snapshot(project_id)
        assert snap.last_event_sequence == 5

        gwt.when("销毁 v1 · v2 重启 · 直接读 events.jsonl 重建 WP 状态")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 可遍历 events 重建 5 个 WP 状态")
        events = list(bus_v2.read_range(project_id))
        assert len(events) == 5

        wp_status = {e["payload"]["wp_id"]: e["payload"]["status"] for e in events}
        assert wp_status == {
            "wp-1": "completed",
            "wp-2": "completed",
            "wp-3": "completed",
            "wp-4": "in_progress",
            "wp-5": "in_progress",
        }


async def test_t3_kb_state_recovery(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T3 · L1-06 KB session events 跨 session 可读."""
    async with gwt("T3 · KB session events 跨 session 持久"):
        gwt.given("v1 · 落 3 条 L1-06:kb_write_committed 事件")
        for kb_id in ["kb-1", "kb-2", "kb-3"]:
            event_bus_v1.append(Event(
                project_id=project_id,
                type="L1-06:kb_write_committed",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"kb_id": kb_id, "kind": "pattern"},
            ))

        gwt.when("销毁 v1 · v2 重启")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 可读 3 条 KB events · payload 一致")
        kb_events = list_events(
            bus_root, project_id, type_exact="L1-06:kb_write_committed",
        )
        # bus_root → event_bus_root alias · list_events 直读 events.jsonl
        kb_ids = [e["payload"]["kb_id"] for e in kb_events]
        assert kb_ids == ["kb-1", "kb-2", "kb-3"]

        gwt.then("v2 仍可继续 append KB 事件(链不断)")
        bus_v2.append(Event(
            project_id=project_id,
            type="L1-06:kb_write_committed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"kb_id": "kb-4-after-restart"},
        ))
        kb_events_v2 = list_events(
            bus_root, project_id, type_exact="L1-06:kb_write_committed",
        )
        assert len(kb_events_v2) == 4


async def test_t4_audit_ledger_continuous(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    gwt: GWT,
) -> None:
    """T4 · audit-ledger hash chain 跨 session 完整(无 gap · prev_hash 串)."""
    async with gwt("T4 · hash chain 跨 v1 + v2 session 完整"):
        gwt.given("v1 落 30 events · 校验链完整")
        append_events(30)
        n_v1 = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_v1 == 30

        gwt.when("销毁 v1 · v2 重启 · 继续 append 20 events")
        del event_bus_v1
        bus_v2 = restart_session()
        for i in range(20):
            bus_v2.append(Event(
                project_id=project_id,
                type="L1-03:test_event",
                actor="planner",
                timestamp=datetime.now(UTC),
                payload={"phase": "v2", "i": i},
            ))

        gwt.then("跨 v1+v2 共 50 events · hash chain 仍连续无 gap")
        n_total = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_total == 50

        gwt.then("seq 1..50 严格连续 (assert_ic_09_hash_chain_intact 校 sequence + prev_hash)")
        # 已隐含在上面


async def test_t5_no_false_halt_after_clean_restart(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    gwt: GWT,
) -> None:
    """T5 · v1 干净退出 → v2 重启不出错 halt(halt_guard marker 应不存在)."""
    async with gwt("T5 · clean restart 不误 halt"):
        gwt.given("v1 正常 append 10 events · 不主动触发 halt")
        append_events(10)
        assert event_bus_v1.halt_guard.is_halted() is False

        gwt.when("销毁 v1 · v2 重启")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 halt_guard 不被误触发 · 状态 READY")
        assert bus_v2.halt_guard.is_halted() is False
        from app.l1_09.event_bus.schemas import BusState
        assert bus_v2.state == BusState.READY

        gwt.then("v2 仍可正常 append 新事件")
        bus_v2.append(Event(
            project_id=project_id,
            type="L1-03:resumed_event",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={"i": 0},
        ))
        # 验证 append 成功 = 总 events == 11
        events = list(bus_v2.read_range(project_id))
        assert len(events) == 11
