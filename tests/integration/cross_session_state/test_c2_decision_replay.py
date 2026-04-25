"""C2 · 决策记录可重放(audit-ledger 重放回 verdict 一致) · 3 TC.

崩溃 mid-tick 后 audit ledger 已落盘的决策事件 · 重启读取 → verdict 与原一致.
重放即从 events.jsonl 反读 payload · 比对原写入 payload.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import list_events


class TestC2DecisionReplay:
    """C2 · audit-ledger 重放 · 3 TC."""

    def test_c2_01_verdict_event_replayable_after_restart(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C2.1: Session 1 写 verdict event · 销毁 bus · Session 2 重启读 · payload 一致."""
        # Session 1
        bus1 = EventBus(event_bus_root)
        original_payload = {
            "verdict": "PASS",
            "verifier_report_id": "vr-001",
            "wp_id": "wp-001",
            "score": 0.95,
        }
        evt = Event(
            project_id=project_id,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload=dict(original_payload),
            timestamp=datetime.now(UTC),
        )
        bus1.append(evt)
        del bus1
        # Session 2
        bus2 = EventBus(event_bus_root)
        events = list_events(
            event_bus_root, project_id,
            type_exact="L1-04:verifier_report_issued",
        )
        assert len(events) == 1
        # payload 完整保留
        assert events[0]["payload"] == original_payload
        # 用 read_range 校 verify_hash_on_read=True
        replayed = list(bus2.read_range(project_id, verify_hash_on_read=True))
        assert len(replayed) == 1
        assert replayed[0]["payload"] == original_payload

    def test_c2_02_multiple_decisions_replayable_in_order(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C2.2: 多条 decision_made 事件 · 重启后按 sequence 顺序 replay 一致."""
        bus1 = EventBus(event_bus_root)
        decisions = [
            {"decision_id": "d-1", "action": "transition", "from": "S3", "to": "S4"},
            {"decision_id": "d-2", "action": "rollback", "verdict": "FAIL_L1"},
            {"decision_id": "d-3", "action": "halt", "red_line_id": "HRL-01"},
        ]
        for d in decisions:
            evt = Event(
                project_id=project_id,
                type="L1-01:decision_made",
                actor="main_loop",
                payload=d,
                timestamp=datetime.now(UTC),
            )
            bus1.append(evt)
        del bus1
        # 重启
        bus2 = EventBus(event_bus_root)
        replayed = list(bus2.read_range(project_id, verify_hash_on_read=True))
        assert len(replayed) == 3
        # 顺序 + payload 完整
        for i, d in enumerate(decisions):
            assert replayed[i]["payload"] == d
            assert replayed[i]["sequence"] == i + 1

    def test_c2_03_replay_after_partial_session(
        self,
        event_bus_root: Path,
        project_id: str,
    ) -> None:
        """C2.3: Session 1 写 3 + 崩溃 · Session 2 重启续写 2 · 总链 5 条 · 全 replay 一致.

        模拟"中断写盘 → 重启续写"场景 · 跨 session 链一致.
        """
        # Session 1
        bus1 = EventBus(event_bus_root)
        for i in range(3):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"step": f"s1-{i}"},
                timestamp=datetime.now(UTC),
            )
            bus1.append(evt)
        del bus1
        # Session 2 续写
        bus2 = EventBus(event_bus_root)
        for i in range(2):
            evt = Event(
                project_id=project_id,
                type="L1-04:verifier_report_issued",
                actor="verifier",
                payload={"step": f"s2-{i}"},
                timestamp=datetime.now(UTC),
            )
            bus2.append(evt)
        # Session 3 全量 replay 校
        bus3 = EventBus(event_bus_root)
        replayed = list(bus3.read_range(project_id, verify_hash_on_read=True))
        assert len(replayed) == 5
        steps = [e["payload"]["step"] for e in replayed]
        assert steps == ["s1-0", "s1-1", "s1-2", "s2-0", "s2-1"]
        # sequence 1..5
        seqs = [e["sequence"] for e in replayed]
        assert seqs == [1, 2, 3, 4, 5]
