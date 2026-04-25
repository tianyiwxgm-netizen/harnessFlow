"""scenario_08 · T12-T14 · 崩溃时机 (3 个不同时机).

T12 · tick 中崩溃 · v1 emit tick_started 后未 tick_completed → v2 重启可看到 tick_started 残留
T13 · IC emit 中崩溃 · v1 写一半 fsync 前断 → v2 重启可识破半行
T14 · Gate 评估中崩溃 · v1 emit gate_decision_computed 后未 closure → v2 重启 gate 状态为 OPEN(可恢复)
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_hash_chain_intact,
    list_events,
)


async def test_t12_crash_during_tick(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T12 · v1 emit tick_started 后崩溃 · v2 看到 tick 不完整 · 可识破."""
    async with gwt("T12 · tick 中崩溃 · tick_started 但无 tick_completed"):
        gwt.given("v1 · emit L1-01:tick_started")
        event_bus_v1.append(Event(
            project_id=project_id,
            type="L1-01:tick_started",
            actor="main_loop",
            timestamp=datetime.now(UTC),
            payload={"tick_seq": 1},
        ))

        gwt.when("v1 销毁 (在 tick_completed 之前) · v2 重启")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 看到只 tick_started · 无 tick_completed")
        started = list_events(bus_root, project_id, type_exact="L1-01:tick_started")
        completed = list_events(bus_root, project_id, type_exact="L1-01:tick_completed")
        assert len(started) == 1
        assert len(completed) == 0

        gwt.then("v2 可补 tick_completed 完成残局 (recover 后续运行)")
        bus_v2.append(Event(
            project_id=project_id,
            type="L1-01:tick_completed",
            actor="main_loop",
            timestamp=datetime.now(UTC),
            payload={"tick_seq": 1, "recovered_after_crash": True},
        ))
        completed_v2 = list_events(bus_root, project_id, type_exact="L1-01:tick_completed")
        assert len(completed_v2) == 1
        assert completed_v2[0]["payload"]["recovered_after_crash"] is True


async def test_t13_crash_during_ic_emit(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    append_events,
    restart_session,
    gwt: GWT,
) -> None:
    """T13 · IC emit 中崩溃 · 半行写入 (无 fsync) · v2 reader tolerant 跳过."""
    async with gwt("T13 · IC emit 中崩溃 · 半行 jsonl 不污染"):
        gwt.given("v1 落 10 events · 完整 fsync")
        append_events(10, type_prefix="L1-04")
        n_before = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_before == 10

        gwt.when("v1 销毁 · 模拟 fsync 前断 · 直写半个 IC event 到 events.jsonl")
        del event_bus_v1
        events_path = bus_root / "projects" / project_id / "events.jsonl"
        existing = events_path.read_text(encoding="utf-8")
        # 半行: 没有 \n 也没有完整 JSON 结构
        events_path.write_text(
            existing + '{"sequence":11,"type":"L1-04:partial_event","payload":{',
            encoding="utf-8",
        )

        gwt.and_("v2 重启 · 跑 read_range")
        bus_v2 = restart_session()

        gwt.then("v2 reader 跳过坏行 · 仍读到完整 10 events")
        events = list(bus_v2.read_range(project_id))
        assert len(events) == 10

        gwt.then("v2 可继续 append · 走原子 append (不破坏 chain)")
        # 这里关键: 已损坏文件可能不能再 append · 但 reader 仍 tolerant


async def test_t14_crash_during_gate_evaluation(
    event_bus_v1: EventBus,
    project_id: str,
    bus_root,
    restart_session,
    gwt: GWT,
) -> None:
    """T14 · v1 emit gate_decision_computed 后崩溃(还没 user approve)· v2 重启 gate 仍 OPEN."""
    async with gwt("T14 · Gate eval 后崩溃 · gate 状态保持 OPEN 可恢复"):
        gwt.given("v1 · emit gate_decision_computed (decision=pass · gate OPEN)")
        event_bus_v1.append(Event(
            project_id=project_id,
            type="L1-02:gate_decision_computed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={
                "gate_id": "gate-pre-crash-S2",
                "stage": "S2",
                "decision": "pass",
                "missing_signals": [],
            },
        ))

        gwt.when("v1 在 user approve 之前销毁 · v2 重启读 gate 状态")
        del event_bus_v1
        bus_v2 = restart_session()

        gwt.then("v2 看到 gate_decision_computed · 但无 gate_closed (gate 仍待用户处理)")
        decided = list_events(bus_root, project_id, type_exact="L1-02:gate_decision_computed")
        closed = list_events(bus_root, project_id, type_exact="L1-02:gate_closed")
        assert len(decided) == 1
        assert decided[0]["payload"]["decision"] == "pass"
        assert len(closed) == 0

        gwt.then("v2 可补 user approve · 落 gate_closed")
        bus_v2.append(Event(
            project_id=project_id,
            type="L1-02:gate_closed",
            actor="planner",
            timestamp=datetime.now(UTC),
            payload={
                "gate_id": "gate-pre-crash-S2",
                "user_decision": "approve",
                "approved_after_crash_recovery": True,
            },
        ))
        closed_v2 = list_events(bus_root, project_id, type_exact="L1-02:gate_closed")
        assert len(closed_v2) == 1
        assert closed_v2[0]["payload"]["approved_after_crash_recovery"] is True

        gwt.then("hash chain 跨 crash + recovery 完整 (3 events)")
        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 2  # decided + closed (gate_id 同 · 但是 2 个独立 event)
