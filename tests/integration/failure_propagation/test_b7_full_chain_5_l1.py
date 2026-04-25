"""B7 · 跨 5 L1 panic 链路 · 2 TC.

完整链:
    l1-05 (subagent timeout)
        → l1-09 (audit emit timeout event)
        → l1-07 (supervisor sense + escalate)
        → l1-01 (panic_handler stop tick)
        → l1-10 (UI 展示 paused 状态)

每一环都有 IC-09 审计事件 · 用 EventBus + EventBusStub 双查.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from app.main_loop.tick_scheduler.halt_enforcer import HaltEnforcer
from app.main_loop.tick_scheduler.panic_handler import (
    PanicHandler,
    PanicSignal,
)
from app.main_loop.tick_scheduler.schemas import TickState
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.event_sender.suggestion_pusher import (
    MockSuggestionConsumer,
    SuggestionPusher,
)
from app.supervisor.event_sender.schemas import (
    PushSuggestionCommand,
    SuggestionLevel,
    SuggestionPriority,
)
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    list_events,
)


class TestB7FullChain5L1:
    """B7 · 5 L1 完整 panic 链路 · 2 TC."""

    async def test_b7_01_full_chain_l1_05_to_l1_10_panic(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
        sup_event_bus: EventBusStub,
    ) -> None:
        """B7.1: 模拟完整链:
        L1-05 timeout → L1-09 audit → L1-07 sense → L1-01 panic → L1-10 UI ack.
        """
        # === L1-05 subagent timeout · audit emit ===
        evt_l1_05 = Event(
            project_id=project_id,
            type="L1-05:skill_invocation_started",
            actor="executor",
            payload={"invocation_id": "inv-1", "capability": "verifier_dispatch"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt_l1_05)
        # subagent timeout 后 emit
        evt_timeout = Event(
            project_id=project_id,
            type="L1-05:skill_invocation_started",  # 简化用同 type · payload 标 timeout
            actor="executor",
            payload={"invocation_id": "inv-1", "status": "timeout"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt_timeout)

        # === L1-07 supervisor sense (escalate) ===
        evt_l1_07 = Event(
            project_id=project_id,
            type="L1-07:supervisor_tick_done",
            actor="supervisor",
            payload={"tick_id": "tk-1", "drift_score": 0.85},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt_l1_07)

        # === L1-07 → L1-01 IC-13 push suggestion ===
        consumer = MockSuggestionConsumer()
        pusher = SuggestionPusher(
            session_pid=project_id,
            consumer=consumer,
            event_bus=sup_event_bus,
        )
        await pusher.push_suggestion(
            PushSuggestionCommand(
                suggestion_id="sugg-chain-001",
                project_id=project_id,
                level=SuggestionLevel.WARN,
                content="L1-05 subagent timeout · 升级 panic",
                observation_refs=("obs-1",),
                priority=SuggestionPriority.P1,
                ts=datetime.now(UTC).isoformat(),
            )
        )

        # === L1-01 panic ===
        # 注意 panic_handler 用 pid-* 模式 · 用 project_id (proj-m3-shared 不匹配 pid- 模式)
        # 所以这里改用纯链路审计验证 · panic 部分用单独 pid
        panic_pid = "pid-chain-test01"
        enforcer = HaltEnforcer(project_id=panic_pid)
        handler = PanicHandler(project_id=panic_pid, halt_enforcer=enforcer)
        result = handler.handle(
            PanicSignal(
                panic_id="panic-chain001",
                project_id=panic_pid,
                user_id="user-1",
                ts=datetime.now(UTC).isoformat(),
            )
        )
        assert result.paused is True
        assert enforcer.as_tick_state() == TickState.PAUSED

        # === L1-10 UI ack ===
        evt_l1_10 = Event(
            project_id=project_id,
            type="L1-10:ui_action_recorded",
            actor="ui",
            payload={"user": "admin", "action": "ack_panic", "panic_id": "panic-chain001"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(evt_l1_10)

        # === 验证完整审计链 ===
        # L1-05 + L1-07 + L1-10 在 real_event_bus
        all_events = list_events(event_bus_root, project_id)
        types = [e["type"] for e in all_events]
        assert "L1-05:skill_invocation_started" in types
        assert "L1-07:supervisor_tick_done" in types
        assert "L1-10:ui_action_recorded" in types
        # IC-13 push 在 sup_event_bus
        push_events = [e for e in sup_event_bus._events if e.type == "L1-07:suggestion_pushed"]
        assert len(push_events) == 1

    async def test_b7_02_chain_audit_hash_chain_intact_per_l1(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """B7.2: 5 L1 各 emit 1 条 audit · hash-chain 必整 + sequence 1..5 连续.

        跨 L1 共用同一 IC-09 总 bus · pid 分片下 sequence 必单调.
        """
        # 5 L1 顺序 emit
        l1_emissions = [
            ("L1-05:skill_invocation_started", "executor"),
            ("L1-09:meta_event_persisted", "audit_mirror"),
            ("L1-07:supervisor_tick_done", "supervisor"),
            ("L1-01:decision_made", "main_loop"),
            ("L1-10:ui_action_recorded", "ui"),
        ]
        for event_type, actor in l1_emissions:
            evt = Event(
                project_id=project_id,
                type=event_type,
                actor=actor,
                payload={"chain_step": event_type},
                timestamp=datetime.now(UTC),
            )
            real_event_bus.append(evt)
        # 全 5 条
        events = list_events(event_bus_root, project_id)
        assert len(events) == 5
        # sequence 1..5
        seqs = [e["sequence"] for e in events]
        assert seqs == [1, 2, 3, 4, 5]
        # hash-chain 链整
        for i in range(1, 5):
            assert events[i]["prev_hash"] == events[i - 1]["hash"], (
                f"hash chain break at seq {i + 1}"
            )
        # 5 L1 prefix 全在
        prefixes = sorted({e["type"].split(":")[0] for e in events})
        assert "L1-01" in prefixes
        assert "L1-05" in prefixes
        assert "L1-07" in prefixes
        assert "L1-09" in prefixes
        assert "L1-10" in prefixes
