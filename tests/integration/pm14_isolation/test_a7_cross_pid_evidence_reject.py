"""A7 · PM-14 跨 pid 引用 evidence reject as audit fault · 4 TC.

PM-14 §1: 跨 pid 引用是审计反模式. event.payload / links 中若引用其他 pid 的
event_id / artifact · 必须被消费方拒(BusWriteFailed-like 或下游 verifier reject).

测试范围:
- A7.1: A 写一条事件 · payload.evidence_event_id 引用 B 的不存在 event · 应可写但下游审计可发现
- A7.2: links 字段含跨 pid 的 ref · 应可写(本身 schema 不拒) · 但下游审计扫描可标记
- A7.3: A 的 audit-ledger 看不到 B 的 event_id · 跨 pid 反向引用断链
- A7.4: project_id='system' 与普通 pid 在同一查询里互相不见
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


class TestA7CrossPidEvidenceReject:
    """A7 · 跨 pid evidence/links 引用审计 · 4 TC."""

    def test_a7_01_a_event_with_b_evidence_id_does_not_create_b_shard(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A7.1: A 写事件 payload.evidence_event_id='evt_b_xxx' · 仅 A 分片有事件.

        即使 payload 引用了 B 的虚拟 event_id · A 的 append 不会在 B 分片创建任何事件.
        审计上: A 分片有事件 + payload 含跨 pid 引用 = 审计扫描可识别.
        """
        pid_a, pid_b = two_pids
        write_event_to(
            pid_a,
            event_type="L1-04:verifier_report_issued",
            payload={"evidence_event_id": f"evt_belongs_to_{pid_b}"},
        )
        # A 分片 1 条
        events_a = assert_ic_09_emitted(
            event_bus_root,
            project_id=pid_a,
            event_type="L1-04:verifier_report_issued",
        )
        assert events_a[0]["payload"]["evidence_event_id"] == f"evt_belongs_to_{pid_b}"
        # B 分片绝对零
        assert_no_events_for_pid(event_bus_root, project_id=pid_b)

    def test_a7_02_a_event_with_links_to_b_does_not_pollute_b_shard(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
    ) -> None:
        """A7.2: A 写事件 · links 含跨 pid 的 ref · B 分片仍空.

        links: list[dict] 不限制 ref 内容 · 但物理写不会泄到 B 分片.
        """
        from datetime import UTC, datetime

        pid_a, pid_b = two_pids
        evt_a = Event(
            project_id=pid_a,
            type="L1-04:verifier_report_issued",
            actor="verifier",
            payload={"verdict": "FAIL_L1"},
            links=[{"kind": "evidence", "ref": f"event:{pid_b}/evt_xxx"}],
            timestamp=datetime.now(UTC),
        )
        result = real_event_bus.append(evt_a)
        assert result.persisted is True
        # 物理只有 A 分片
        events_a = list_events(event_bus_root, pid_a)
        assert len(events_a) == 1
        assert events_a[0]["links"][0]["ref"] == f"event:{pid_b}/evt_xxx"
        assert_no_events_for_pid(event_bus_root, project_id=pid_b)

    def test_a7_03_b_audit_query_cannot_see_a_event_by_id(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A7.3: A 写一条事件 · 拿到 event_id · 在 B 分片查 events · 看不到.

        反向断链: A 的 event_id 在 B audit-query 不存在 · 即使知道 id.
        """
        pid_a, pid_b = two_pids
        result_a = write_event_to(pid_a, event_type="L1-04:verifier_report_issued")
        evt_id_a = result_a.event_id
        # B 分片查所有 type · 永远找不到 evt_id_a
        b_events = list_events(event_bus_root, pid_b)
        assert b_events == []
        # 直接物理路径校 · B 分片连目录都没建(write_event_to 只写 A)
        b_path = event_bus_root / "projects" / pid_b / "events.jsonl"
        if b_path.exists():
            for raw in b_path.read_bytes().splitlines():
                if raw.strip():
                    import json
                    e = json.loads(raw.decode("utf-8"))
                    assert e.get("event_id") != evt_id_a, (
                        f"PM-14 反向断链违反: A 的 event_id {evt_id_a} 不应在 B 分片"
                    )

    def test_a7_04_system_pid_isolated_from_normal_pid(
        self,
        real_event_bus: EventBus,
        event_bus_root: Path,
        two_pids: tuple[str, str],
        write_event_to,
    ) -> None:
        """A7.4: 'system' pid 与普通 pid 完全隔离.

        IC-09 系统级事件分片 vs 业务 pid 分片 · 同一 EventBus 但物理切片.
        """
        pid_a, _pid_b = two_pids
        # 业务事件
        write_event_to(pid_a, event_type="L1-04:verifier_report_issued")
        # 系统事件(如 halt 监测)
        from datetime import UTC, datetime

        sys_evt = Event(
            project_id="system",
            type="L1-09:meta_event_persisted",
            actor="audit_mirror",
            payload={"self_event_id": "evt_sys_test"},
            timestamp=datetime.now(UTC),
        )
        real_event_bus.append(sys_evt)
        # A 分片只有 verifier · system 分片只有 meta
        a_events = list_events(event_bus_root, pid_a)
        sys_events = list_events(event_bus_root, "system")
        assert len(a_events) == 1
        assert len(sys_events) == 1
        assert a_events[0]["type"] == "L1-04:verifier_report_issued"
        assert sys_events[0]["type"] == "L1-09:meta_event_persisted"
        # 互不污染
        assert a_events[0]["project_id"] == pid_a
        assert sys_events[0]["project_id"] == "system"
