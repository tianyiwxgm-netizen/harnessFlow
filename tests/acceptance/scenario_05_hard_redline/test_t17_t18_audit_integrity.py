"""Scenario 05 · T17-T18 · 审计完整性 (hash chain · retention=permanent · cross-session 持久).

2 TC:
- T17 hash chain 完整性 · 多次 halt 入账 · seq 单调 + prev_hash 串正确
- T18 cross-session 持久 · 第二次起新 EventBus 读旧 events.jsonl · audit 不丢
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.main_loop.supervisor_receiver.ic_15_consumer import IC15Consumer
from app.main_loop.supervisor_receiver.schemas import HaltSignal
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.supervisor.event_sender.schemas import (
    HardHaltEvidence,
    RequestHardHaltCommand,
)
from tests.shared.gwt_helpers import GWT
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_ic_09_hash_chain_intact,
    list_events,
)


# ============================================================================
# T17 · hash chain 完整 · 多次 halt 入账 · seq 单调 + prev_hash 串正确
# ============================================================================


async def test_t17_hash_chain_intact_after_multiple_halts(
    real_event_bus: EventBus,
    event_bus_root: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T17 · 5 类红线各起独立 enforcer + consumer (避幂等) · 5 hard_halted 入账.

    验证:
    1. seq 1..5 连续
    2. prev_hash 链每条对齐前一条
    3. hash chain intact (assert_ic_09_hash_chain_intact)
    4. 顺序保留 (按 append 顺序)
    """
    from tests.acceptance.scenario_05_hard_redline.conftest import (
        _AsyncEventBusAdapter,
    )

    async with gwt("T17 · hash chain 完整 · 5 halt 入账 + chain 无 gap"):
        gwt.given("real EventBus 干净 · audit empty")
        adapter = _AsyncEventBusAdapter(real_event_bus, project_id)

        gwt.when("5 类红线 (HRL-01~05) · 各起独立 enforcer/consumer · 顺序入账")
        halt_ids = []
        for idx, hrl in enumerate(["HRL-01", "HRL-02", "HRL-03", "HRL-04", "HRL-05"]):
            enforcer = HaltEnforcer(project_id=project_id)
            consumer = IC15Consumer(
                session_pid=project_id,
                halt_target=enforcer,
                event_bus=adapter,
            )
            halt_id = f"halt-t17-seq{idx+1}"
            cmd = RequestHardHaltCommand(
                halt_id=halt_id,
                project_id=project_id,
                red_line_id=hrl,
                evidence=HardHaltEvidence(
                    observation_refs=(f"ev-t17-{idx+1}-a", f"ev-t17-{idx+1}-b"),
                    confirmation_count=2,
                ),
                require_user_authorization=True,
                ts=datetime.now(UTC).isoformat(),
            )
            signal = HaltSignal.from_command(cmd, received_at_ms=0)
            await consumer.consume(signal)
            halt_ids.append(halt_id)

        gwt.then("hash chain intact · 5 events · seq 1..5 连续")
        n = assert_ic_09_hash_chain_intact(event_bus_root, project_id=project_id)
        assert n == 5

        gwt.then("5 条 hard_halted 顺序保留 · 各对应 halt_id")
        events = list_events(
            event_bus_root, project_id, type_exact="L1-01:hard_halted",
        )
        assert len(events) == 5
        for idx, evt in enumerate(events):
            assert evt["payload"]["halt_id"] == halt_ids[idx]
            assert evt["sequence"] == idx + 1

        gwt.then("第 N 条的 prev_hash 串到第 N-1 的 hash")
        for i in range(1, len(events)):
            assert events[i]["prev_hash"] == events[i - 1]["hash"]


# ============================================================================
# T18 · cross-session 持久 · 重启 EventBus 后 audit 仍在
# ============================================================================


async def test_t18_audit_persists_across_session_restart(
    tmp_path: Path,
    project_id: str,
    gwt: GWT,
) -> None:
    """T18 · session A 写 halt audit → close → session B 读旧 events.jsonl."""
    from tests.acceptance.scenario_05_hard_redline.conftest import (
        _AsyncEventBusAdapter,
    )

    async with gwt("T18 · cross-session 审计持久 · 旧 events.jsonl 完整可读"):
        gwt.given("session A · 全新 EventBus + halt 1 次")
        bus_root = tmp_path / "persistent_bus"
        bus_root.mkdir(parents=True)
        bus_a = EventBus(bus_root)
        adapter_a = _AsyncEventBusAdapter(bus_a, project_id)
        enforcer_a = HaltEnforcer(project_id=project_id)
        consumer_a = IC15Consumer(
            session_pid=project_id,
            halt_target=enforcer_a,
            event_bus=adapter_a,
        )

        halt_id = "halt-t18-cross-session"
        cmd = RequestHardHaltCommand(
            halt_id=halt_id,
            project_id=project_id,
            red_line_id="HRL-01",
            evidence=HardHaltEvidence(
                observation_refs=("ev-cross-1", "ev-cross-2"),
                confirmation_count=2,
            ),
            require_user_authorization=True,
            ts=datetime.now(UTC).isoformat(),
        )
        await consumer_a.consume(HaltSignal.from_command(cmd, received_at_ms=0))

        gwt.when("session A 关 · session B 起 · 同一 bus_root")
        del bus_a, consumer_a, enforcer_a, adapter_a
        # 模拟新进程
        bus_b = EventBus(bus_root)

        gwt.then("session B 读 events.jsonl · 看到 hard_halted 仍在 + chain intact")
        events = list_events(
            bus_root, project_id, type_exact="L1-01:hard_halted",
        )
        assert len(events) == 1
        assert events[0]["payload"]["halt_id"] == halt_id

        n = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n == 1

        gwt.then("session B 可继续 append (chain 不断)")
        adapter_b = _AsyncEventBusAdapter(bus_b, project_id)
        enforcer_b = HaltEnforcer(project_id=project_id)
        consumer_b = IC15Consumer(
            session_pid=project_id,
            halt_target=enforcer_b,
            event_bus=adapter_b,
        )
        cmd2 = RequestHardHaltCommand(
            halt_id="halt-t18-session-b-2nd",
            project_id=project_id,
            red_line_id="HRL-02",
            evidence=HardHaltEvidence(
                observation_refs=("ev-b-1", "ev-b-2"),
                confirmation_count=2,
            ),
            require_user_authorization=True,
            ts=datetime.now(UTC).isoformat(),
        )
        await consumer_b.consume(HaltSignal.from_command(cmd2, received_at_ms=0))

        # chain 共 2 条 · seq 1, 2
        events2 = list_events(
            bus_root, project_id, type_exact="L1-01:hard_halted",
        )
        assert len(events2) == 2
        assert events2[0]["sequence"] == 1
        assert events2[1]["sequence"] == 2
        assert events2[1]["prev_hash"] == events2[0]["hash"]

        # chain 整体 intact
        n_total = assert_ic_09_hash_chain_intact(bus_root, project_id=project_id)
        assert n_total == 2
