"""WP-α-09 · L2-03 AuditQuery · IC-18 query_audit_trail.

对齐 3-2 L2-03 tests.md · 核心路径 + 3 anchor_type + filter + gap detect.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.l1_09.audit import (
    Anchor,
    AnchorType,
    AuditGate,
    AuditGateClosed,
    AuditGateRebuilding,
    AuditInvalidStateTransition,
    AuditProjectRequired,
    AuditQuery,
    AuditRotation,
    AuditWriter,
    Completeness,
    GateStateEnum,
    LayerType,
    QueryFilter,
    paginate,
)
from app.l1_09.event_bus import EventBus
from app.l1_09.event_bus.schemas import Event


@pytest.fixture
def audit_setup(tmp_fs: Path):
    """准备一个带 5 个事件的 project."""
    bus = EventBus(root=tmp_fs)
    pid = "projaudit"
    for i in range(5):
        evt = Event(
            project_id=pid,
            type=("L1-05:decision_made" if i == 2 else "L1-05:task_done"),  # noqa
            actor="executor",
            payload={"n": i},
            timestamp=datetime.now(UTC),
        )
        bus.append(evt)
    return bus, pid, tmp_fs


# ===================== AuditQuery =====================

class TestAuditQuery:
    def test_TC_L203_001_project_anchor_returns_all(self, audit_setup) -> None:
        bus, pid, root = audit_setup
        q = AuditQuery(root=root)
        anchor = Anchor(
            anchor_type=AnchorType.PROJECT_ID,
            anchor_id=pid,
            project_id=pid,
        )
        trail = q.query_audit_trail(anchor)
        assert trail.project_id == pid
        assert trail.event_layer.count == 5
        assert trail.total_entries >= 5

    def test_TC_L203_002_event_id_anchor_single(self, audit_setup) -> None:
        bus, pid, root = audit_setup
        q = AuditQuery(root=root)
        # 取第 1 个 event 的 id
        first_events = list(bus.read_range(pid))
        target_id = first_events[0]["event_id"]
        anchor = Anchor(
            anchor_type=AnchorType.EVENT_ID,
            anchor_id=target_id,
            project_id=pid,
        )
        trail = q.query_audit_trail(anchor)
        assert trail.event_layer.count == 1

    def test_TC_L203_003_completeness_broken_if_no_decision(self, tmp_fs: Path) -> None:
        """无 decision 事件 · completeness = BROKEN."""
        bus = EventBus(root=tmp_fs)
        pid = "prjnodecide"
        # 只 task_done · 无 decision
        for _ in range(3):
            bus.append(Event(
                project_id=pid,
                type="L1-05:task_done",
                actor="executor",
                payload={},
                timestamp=datetime.now(UTC),
            ))
        q = AuditQuery(root=tmp_fs)
        trail = q.query_audit_trail(Anchor(
            anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid,
        ))
        assert trail.completeness == Completeness.BROKEN
        assert "decision" in trail.broken_layers

    def test_TC_L203_004_filter_by_actor(self, tmp_fs: Path) -> None:
        bus = EventBus(root=tmp_fs)
        pid = "prjactor"
        bus.append(Event(project_id=pid, type="L1-05:a", actor="executor",
                         payload={}, timestamp=datetime.now(UTC)))
        bus.append(Event(project_id=pid, type="L1-05:b", actor="main_loop",
                         payload={}, timestamp=datetime.now(UTC)))
        q = AuditQuery(root=tmp_fs)
        trail = q.query_audit_trail(
            Anchor(anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid),
            QueryFilter(actor="main_loop"),
        )
        assert trail.event_layer.count == 1
        assert trail.event_layer.entries[0]["actor"] == "main_loop"

    def test_TC_L203_005_filter_by_event_type(self, audit_setup) -> None:
        bus, pid, root = audit_setup
        q = AuditQuery(root=root)
        trail = q.query_audit_trail(
            Anchor(anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid),
            QueryFilter(event_type="L1-05:decision_made"),
        )
        assert trail.event_layer.count == 1
        assert trail.completeness == Completeness.COMPLETE

    def test_TC_L203_006_empty_project_id_raises(self, tmp_fs: Path) -> None:
        q = AuditQuery(root=tmp_fs)
        with pytest.raises(AuditProjectRequired):
            q.query_audit_trail(Anchor(
                anchor_type=AnchorType.PROJECT_ID, anchor_id="x", project_id="",
            ))

    def test_TC_L203_007_truncated_flag(self, tmp_fs: Path) -> None:
        """超过 max_events_per_layer · truncated=True."""
        bus = EventBus(root=tmp_fs)
        pid = "prjtrunc"
        for _ in range(15):
            bus.append(Event(project_id=pid, type="L1-05:task", actor="executor",
                             payload={}, timestamp=datetime.now(UTC)))
        q = AuditQuery(root=tmp_fs)
        trail = q.query_audit_trail(
            Anchor(anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid),
            QueryFilter(max_events_per_layer=10),
        )
        assert trail.truncated
        assert trail.event_layer.count == 10

    def test_TC_L203_008_hash_chain_gap_reported(self, audit_setup) -> None:
        """正常无 gap · gaps 为空."""
        bus, pid, root = audit_setup
        q = AuditQuery(root=root)
        trail = q.query_audit_trail(
            Anchor(anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid),
        )
        assert trail.hash_chain_gap == []

    def test_TC_L203_009_latency_tracked(self, audit_setup) -> None:
        bus, pid, root = audit_setup
        q = AuditQuery(root=root)
        trail = q.query_audit_trail(
            Anchor(anchor_type=AnchorType.PROJECT_ID, anchor_id=pid, project_id=pid),
        )
        assert trail.latency_ms >= 0
        assert trail.latency_ms < 1000  # 1000ms deadline


# ===================== Pagination =====================

class TestPaginator:
    def test_TC_L203_020_paginate_full(self) -> None:
        items = list(range(10))
        page = paginate(items, cursor=0, page_size=3)
        assert page.items == [0, 1, 2]
        assert page.next_cursor == 3
        assert page.total == 10

    def test_TC_L203_021_paginate_last(self) -> None:
        items = list(range(10))
        page = paginate(items, cursor=9, page_size=3)
        assert page.items == [9]
        assert page.next_cursor is None


# ===================== WP10 · Gate state machine =====================

class TestAuditGate:
    def test_TC_L203_030_gate_initial_open(self) -> None:
        gate = AuditGate("p1")
        assert gate.state == GateStateEnum.OPEN

    def test_TC_L203_031_open_to_closed_allowed(self) -> None:
        gate = AuditGate("p1")
        gate.transition(GateStateEnum.CLOSED, reason="halt")
        assert gate.state == GateStateEnum.CLOSED

    def test_TC_L203_032_closed_to_rebuilding_allowed(self) -> None:
        gate = AuditGate("p1", initial_state=GateStateEnum.CLOSED)
        gate.transition(GateStateEnum.REBUILDING, reason="restart")
        assert gate.state == GateStateEnum.REBUILDING

    def test_TC_L203_033_rebuilding_to_open_requires_authz(self) -> None:
        gate = AuditGate("p1", initial_state=GateStateEnum.REBUILDING)
        with pytest.raises(AuditInvalidStateTransition):
            gate.transition(GateStateEnum.OPEN, reason="done", caller="hacker")
        gate.transition(GateStateEnum.OPEN, reason="done", caller="L2-04:on_system_resumed")
        assert gate.state == GateStateEnum.OPEN

    def test_TC_L203_034_check_open_raises_on_closed(self) -> None:
        gate = AuditGate("p1", initial_state=GateStateEnum.CLOSED)
        with pytest.raises(AuditGateClosed):
            gate.check_open_or_raise()

    def test_TC_L203_035_check_open_raises_on_rebuilding(self) -> None:
        gate = AuditGate("p1", initial_state=GateStateEnum.REBUILDING)
        with pytest.raises(AuditGateRebuilding):
            gate.check_open_or_raise()

    def test_TC_L203_036_rebuilding_to_closed_allowed(self) -> None:
        """REBUILDING → CLOSED 被允许（降级路径）."""
        gate = AuditGate("p1", initial_state=GateStateEnum.REBUILDING)
        gate.transition(GateStateEnum.CLOSED, reason="rebuild_failed")
        assert gate.state == GateStateEnum.CLOSED


# ===================== WP10 · Rotation =====================

class TestAuditRotation:
    def test_TC_L203_040_rotate_by_size(self, tmp_fs: Path) -> None:
        audit_path = tmp_fs / "audit.jsonl"
        audit_path.write_bytes(b"x" * 50)
        r = AuditRotation(audit_path, size_limit=10)
        assert r.should_rotate_by_size()
        archived = r.rotate()
        assert archived is not None
        assert archived.exists()
        # 新文件空
        assert audit_path.stat().st_size == 0

    def test_TC_L203_041_rotate_no_trigger_small(self, tmp_fs: Path) -> None:
        audit_path = tmp_fs / "audit.jsonl"
        audit_path.write_bytes(b"x" * 5)
        r = AuditRotation(audit_path, size_limit=100)
        assert not r.should_rotate_by_size()

    def test_TC_L203_042_list_archives(self, tmp_fs: Path) -> None:
        audit_path = tmp_fs / "audit.jsonl"
        audit_path.write_bytes(b"x" * 50)
        r = AuditRotation(audit_path, size_limit=10)
        r.rotate()
        audit_path.write_bytes(b"y" * 50)
        r.rotate()
        assert len(r.list_archives()) == 2


# ===================== WP10 · Writer =====================

class TestAuditWriter:
    def test_TC_L203_050_record_audit_writes_event(self, tmp_fs: Path) -> None:
        bus = EventBus(root=tmp_fs)
        registry = None  # no-op for writer
        writer = AuditWriter(bus, registry)
        aid = writer.record_audit(
            project_id="prjwrite",
            action="gate_transition",
            actor="recoverer",
            payload={"from": "OPEN", "to": "CLOSED"},
        )
        assert aid.startswith("audit_")
        # 验证写入
        events = list(bus.read_range("prjwrite"))
        assert len(events) == 1
        assert events[0]["type"] == "L1-09:audit_gate_transition"
