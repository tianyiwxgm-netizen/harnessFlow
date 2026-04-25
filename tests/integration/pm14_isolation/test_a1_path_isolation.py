"""A1 · 路径隔离 · 写 A 的 audit-ledger 不出现在 B(IC-09 + IC-18) · 5 TC.

PM-14 §1 铁律: events.jsonl 物理分片 projects/<pid>/ · 跨 pid 严格隔离.
查 B 分片的 audit-ledger · 永远查不到 A 写入的事件.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.l1_09.event_bus.core import EventBus
from app.l1_09.event_bus.schemas import Event
from tests.shared.ic_assertions import (
    assert_ic_09_emitted,
    assert_no_events_for_pid,
    list_events,
)


class TestA1PathIsolation:
    """A1 · IC-09 路径隔离 5 TC."""

    def test_a1_01_a_event_does_not_appear_in_b(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A1.1: 写 A 一条 verifier_report_issued · B 分片无任何事件.

        IC-09 物理路径 PM-14 切片: projects/A/events.jsonl ≠ projects/B/events.jsonl.
        """
        pid_a, pid_b = two_pids
        write_event_to(pid_a, event_type="L1-04:verifier_report_issued")
        # A 有 1 条
        assert_ic_09_emitted(
            event_bus_root,
            project_id=pid_a,
            event_type="L1-04:verifier_report_issued",
            min_count=1,
        )
        # B 完全无事件(零泄漏)
        assert_no_events_for_pid(event_bus_root, project_id=pid_b)

    def test_a1_02_a_writes_5_b_unaffected(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A1.2: A 写 5 条不同 type · B 始终零事件."""
        pid_a, pid_b = two_pids
        for t in [
            "L1-01:decision_made",
            "L1-02:state_transitioned",
            "L1-03:wp_scheduled",
            "L1-04:verifier_report_issued",
            "L1-07:supervisor_tick_done",
        ]:
            actor = "main_loop" if not t.startswith("L1-04") else "verifier"
            if t.startswith("L1-07"):
                actor = "supervisor"
            elif t.startswith("L1-03"):
                actor = "executor"
            write_event_to(pid_a, event_type=t, actor=actor)
        # A 分片 5 条
        events_a = list_events(event_bus_root, pid_a)
        assert len(events_a) == 5
        # B 分片 0 条
        assert_no_events_for_pid(event_bus_root, project_id=pid_b)

    def test_a1_03_b_writes_first_a_isolated(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A1.3: 反向 · B 先写 · A 仍零事件."""
        pid_a, pid_b = two_pids
        write_event_to(pid_b, event_type="L1-04:verifier_report_issued")
        assert_ic_09_emitted(
            event_bus_root,
            project_id=pid_b,
            event_type="L1-04:verifier_report_issued",
        )
        assert_no_events_for_pid(event_bus_root, project_id=pid_a)

    def test_a1_04_interleaved_writes_separate_shards(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A1.4: A/B 交错写 · 每分片只看到自己的事件."""
        pid_a, pid_b = two_pids
        # 交错: A B A B A B
        write_event_to(pid_a, event_type="L1-04:verifier_report_issued")
        write_event_to(pid_b, event_type="L1-04:verifier_report_issued")
        write_event_to(pid_a, event_type="L1-01:decision_made", actor="main_loop")
        write_event_to(pid_b, event_type="L1-01:decision_made", actor="main_loop")
        write_event_to(pid_a, event_type="L1-02:state_transitioned", actor="main_loop")
        write_event_to(pid_b, event_type="L1-02:state_transitioned", actor="main_loop")
        # A 3 条 · B 3 条 · 互不污染
        events_a = list_events(event_bus_root, pid_a)
        events_b = list_events(event_bus_root, pid_b)
        assert len(events_a) == 3
        assert len(events_b) == 3
        # A 分片下 project_id 字段全为 A
        assert all(e.get("project_id") == pid_a for e in events_a)
        assert all(e.get("project_id") == pid_b for e in events_b)

    def test_a1_05_per_pid_sequence_independent(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A1.5: 每 pid 自己的 sequence 从 1 起 · 互不影响.

        PM-14 §3 sequence 分片独立 · A 写完 5 条 · B 第一条 seq=1 不是 6.
        """
        pid_a, pid_b = two_pids
        for _ in range(5):
            write_event_to(pid_a, event_type="L1-04:verifier_report_issued")
        # B 第 1 条
        result_b = write_event_to(pid_b, event_type="L1-04:verifier_report_issued")
        assert result_b.sequence == 1, (
            f"PM-14 sequence 跨 pid 串了 · B 第一条 seq 期望=1 实际={result_b.sequence}"
        )
        # A 5 条 sequence 1..5
        events_a = list_events(event_bus_root, pid_a)
        assert [e["sequence"] for e in events_a] == [1, 2, 3, 4, 5]
