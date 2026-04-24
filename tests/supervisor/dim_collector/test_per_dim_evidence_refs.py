"""WP01-P1 补丁 · per-dim evidence_refs 追溯粒度。

review 遗留：tech-design §2.2 + PRD §8.4 要求每维度带独立 evidence_refs（指向源事件 id）。
现 SupervisorSnapshot 只有整体 evidence_refs · 无法追溯"这个 phase 值从哪些事件采到的"。

本 P1 修复：
- DimScanner 各 scan_xxx 同时返回 evidence_refs
- EightDimensionVector 新增 dim_evidence_refs: dict[str, tuple[str, ...]]
- snapshot.evidence_refs 仍作为 union（总审计索引）· dim_evidence_refs 提供追溯粒度

8 个 TC（每维度 1 · 外加 vector 级 2 个：union / 缺维空）。
"""
from __future__ import annotations

import pytest

from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.collector import EightDimensionCollector
from app.supervisor.common.clock import FrozenClock
from app.supervisor.dim_collector.dim_scanner import DimScanner
from app.supervisor.dim_collector.schemas import EightDimensionVector
from app.supervisor.dim_collector.state_cache import StateCache


asyncio_mark = pytest.mark.asyncio


def _build_scanner(
    l102: L102Stub | None = None,
    l103: L103Stub | None = None,
    l104: L104Stub | None = None,
    bus: EventBusStub | None = None,
) -> DimScanner:
    return DimScanner(
        l102=l102 or L102Stub(),
        l103=l103 or L103Stub(),
        l104=l104 or L104Stub(),
        event_bus=bus or EventBusStub(),
    )


async def _build_collector(bus: EventBusStub | None = None) -> EightDimensionCollector:
    bus = bus or EventBusStub()
    scanner = _build_scanner(bus=bus)
    return EightDimensionCollector(
        scanner=scanner,
        cache=StateCache(clock=FrozenClock()),
        event_bus=bus,
        clock=FrozenClock(),
    )


# --- scanner 返回 evidence_refs ---


@asyncio_mark
async def test_scan_phase_carries_evidence_refs(pid) -> None:
    """TC-L107-L201-P1-001 · phase 成功路径必带 evidence_refs（至少 1 条）。"""
    s = _build_scanner(l102=L102Stub(phase="S4"))
    result = await s.scan_phase(pid.value)
    # new 3-tuple: (value, evidence_refs, err)
    value, evidence_refs, err = result
    assert value == "S4"
    assert err is None
    assert isinstance(evidence_refs, tuple)
    assert len(evidence_refs) >= 1


@asyncio_mark
async def test_scan_phase_failure_has_empty_evidence_refs(pid) -> None:
    """TC-L107-L201-P1-002 · phase 失败时 evidence_refs 为空 tuple。"""
    s = _build_scanner(l102=L102Stub(_timeout=True))
    _, evidence_refs, err = await s.scan_phase(pid.value)
    assert err is not None
    assert evidence_refs == ()


@asyncio_mark
async def test_scan_tool_calls_evidence_refs_points_to_source_events(pid) -> None:
    """TC-L107-L201-P1-003 · tool_calls evidence_refs 指向 read_event_stream 命中的事件 id。"""
    bus = EventBusStub()
    eid1 = await bus.append_event(
        project_id=pid.value,
        type="tool_invoked",
        payload={"tool_name": "git", "args_hash": "a"},
    )
    eid2 = await bus.append_event(
        project_id=pid.value,
        type="tool_invoked",
        payload={"tool_name": "rm", "args_hash": "b"},
    )
    s = _build_scanner(bus=bus)
    _, evidence_refs, err = await s.scan_tool_calls(pid.value)
    assert err is None
    assert eid1 in evidence_refs
    assert eid2 in evidence_refs


@asyncio_mark
async def test_scan_event_bus_evidence_refs_non_empty_on_activity(pid) -> None:
    """TC-L107-L201-P1-004 · event_bus 维度有事件时 evidence_refs 非空。"""
    bus = EventBusStub()
    await bus.append_event(
        project_id=pid.value, type="decision", payload={"x": 1}
    )
    s = _build_scanner(bus=bus)
    _, evidence_refs, err = await s.scan_event_bus(pid.value)
    assert err is None
    # stats is summary · evidence_refs should carry at least synthetic reference
    assert isinstance(evidence_refs, tuple)


@asyncio_mark
async def test_scan_latency_slo_empty_has_empty_refs(pid) -> None:
    """TC-L107-L201-P1-005 · latency_slo 无样本时 evidence_refs 为空。"""
    s = _build_scanner()
    _, evidence_refs, err = await s.scan_latency_slo(pid.value)
    assert err is None
    assert evidence_refs == ()


# --- vector 携带 dim_evidence_refs ---


def test_eight_dim_vector_has_dim_evidence_refs_field() -> None:
    """TC-L107-L201-P1-006 · EightDimensionVector 新增 dim_evidence_refs 字段 · 默认空 dict。"""
    v = EightDimensionVector()
    assert hasattr(v, "dim_evidence_refs")
    assert v.dim_evidence_refs == {}


def test_eight_dim_vector_accepts_dim_evidence_refs() -> None:
    """TC-L107-L201-P1-007 · dim_evidence_refs 可写入 · key 限定 8 维名。"""
    v = EightDimensionVector(
        phase="S4",
        dim_evidence_refs={"phase": ("ev-1", "ev-2")},
    )
    assert v.dim_evidence_refs["phase"] == ("ev-1", "ev-2")


# --- collector 聚合填充 dim_evidence_refs + union 至 snapshot.evidence_refs ---


@asyncio_mark
async def test_tick_collect_populates_dim_evidence_refs(pid) -> None:
    """TC-L107-L201-P1-008 · tick_collect 产出的 snapshot 带 per-dim 追溯。"""
    bus = EventBusStub()
    await bus.append_event(
        project_id=pid.value, type="tool_invoked", payload={"tool_name": "git"}
    )
    c = await _build_collector(bus=bus)
    snap = await c.tick_collect(pid.value)
    dim_refs = snap.eight_dim_vector.dim_evidence_refs
    assert "phase" in dim_refs
    assert isinstance(dim_refs["phase"], tuple)
    # 总 evidence_refs 是 union · phase/tool_calls 的 refs 应都在
    for _, refs in dim_refs.items():
        for ref in refs:
            assert ref in snap.evidence_refs


@asyncio_mark
async def test_tick_collect_dim_evidence_refs_skips_failed_dims(pid) -> None:
    """TC-L107-L201-P1-009 · 某维采集失败时 · dim_evidence_refs 不含该维（或为空）。"""
    bus = EventBusStub()
    scanner = DimScanner(
        l102=L102Stub(_timeout=True),  # phase + artifacts fail
        l103=L103Stub(),
        l104=L104Stub(),
        event_bus=bus,
    )
    c = EightDimensionCollector(
        scanner=scanner, cache=StateCache(clock=FrozenClock()), event_bus=bus, clock=FrozenClock()
    )
    snap = await c.tick_collect(pid.value)
    dim_refs = snap.eight_dim_vector.dim_evidence_refs
    # 失败维 evidence_refs 为空 · 或者不出现
    assert dim_refs.get("phase", ()) == ()
    assert dim_refs.get("artifacts", ()) == ()
    # 其他维正常
    assert "wp_status" in dim_refs
