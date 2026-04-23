"""DimScanner · 8 维独立 scanner + per-dim 错误隔离 + asyncio.gather 并行。

覆盖：
- 每维正常路径（8）
- 每维错误路径（IC timeout / unavailable 映射到 SupervisorError）
- scan_all 聚合 · 单维失败不影响他维
"""
from __future__ import annotations

import pytest

from app.supervisor.common.errors import SupervisorError
from app.supervisor.common.event_bus_stub import EventBusStub
from app.supervisor.common.ic_stubs import L102Stub, L103Stub, L104Stub
from app.supervisor.dim_collector.dim_scanner import DimScanner


pytestmark = pytest.mark.asyncio


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


# --- phase (IC-L1-02 read_lifecycle_state) ---

async def test_scan_phase_returns_s4(pid) -> None:
    s = _build_scanner(l102=L102Stub(phase="S4"))
    value, err = await s.scan_phase(pid.value)
    assert value == "S4"
    assert err is None


async def test_scan_phase_timeout_maps_to_ic_l1_02_timeout(pid) -> None:
    s = _build_scanner(l102=L102Stub(_timeout=True))
    value, err = await s.scan_phase(pid.value)
    assert value is None
    assert err == SupervisorError.IC_L1_02_TIMEOUT


async def test_scan_phase_unavailable_maps_to_ic_l1_02_unavailable(pid) -> None:
    s = _build_scanner(l102=L102Stub(_unavailable=True))
    value, err = await s.scan_phase(pid.value)
    assert value is None
    assert err == SupervisorError.IC_L1_02_UNAVAILABLE


# --- artifacts ---

async def test_scan_artifacts_returns_completeness(pid) -> None:
    s = _build_scanner(l102=L102Stub(artifacts_completeness_pct=95.5))
    value, err = await s.scan_artifacts(pid.value)
    assert err is None
    assert value["completeness_pct"] == 95.5


async def test_scan_artifacts_timeout(pid) -> None:
    s = _build_scanner(l102=L102Stub(_timeout=True))
    value, err = await s.scan_artifacts(pid.value)
    assert value is None and err == SupervisorError.IC_L1_02_TIMEOUT


# --- wp_status ---

async def test_scan_wp_status_computes_completion_pct(pid) -> None:
    s = _build_scanner(l103=L103Stub(total=20, completed=5))
    value, err = await s.scan_wp_status(pid.value)
    assert err is None
    assert value["completion_pct"] == 25.0


async def test_scan_wp_status_timeout(pid) -> None:
    s = _build_scanner(l103=L103Stub(_timeout=True))
    value, err = await s.scan_wp_status(pid.value)
    assert value is None and err == SupervisorError.IC_L1_03_TIMEOUT


# --- self_repair_rate ---

async def test_scan_self_repair_rate(pid) -> None:
    s = _build_scanner(l104=L104Stub(attempts=10, successes=7))
    value, err = await s.scan_self_repair_rate(pid.value)
    assert err is None and value["rate"] == 0.7


async def test_scan_self_repair_rate_timeout(pid) -> None:
    s = _build_scanner(l104=L104Stub(_timeout=True))
    value, err = await s.scan_self_repair_rate(pid.value)
    assert value is None and err == SupervisorError.IC_L1_04_TIMEOUT


# --- rollback_counter ---

async def test_scan_rollback_counter(pid) -> None:
    s = _build_scanner(
        l104=L104Stub(rollback_count=3, rollback_reasons={"L2_verdict": 3})
    )
    value, err = await s.scan_rollback_counter(pid.value)
    assert err is None and value["count"] == 3


# --- event_bus ---

async def test_scan_event_bus_stats_reflects_appended_events(pid) -> None:
    bus = EventBusStub()
    await bus.append_event(project_id=pid.value, type="decision", payload={"x": 1})
    s = _build_scanner(bus=bus)
    value, err = await s.scan_event_bus(pid.value)
    assert err is None and value["event_count_last_30s"] == 1


# --- tool_calls ---

async def test_scan_tool_calls_extracts_last_and_detects_red_line_candidate(pid) -> None:
    bus = EventBusStub()
    await bus.append_event(
        project_id=pid.value,
        type="tool_invoked",
        payload={"tool_name": "git", "args_hash": "abc"},
    )
    s = _build_scanner(bus=bus)
    value, err = await s.scan_tool_calls(pid.value)
    assert err is None
    assert value["last_tool_name"] == "git"
    assert value["red_line_candidate"] is True  # git is red-line candidate


async def test_scan_tool_calls_no_events_returns_empty(pid) -> None:
    s = _build_scanner()
    value, err = await s.scan_tool_calls(pid.value)
    assert err is None
    assert value["last_tool_name"] is None
    assert value["red_line_candidate"] is False
    assert value["last_n_calls"] == []


# --- latency_slo ---

async def test_scan_latency_slo_computes_percentiles(pid) -> None:
    bus = EventBusStub()
    for i in range(10):
        await bus.append_event(
            project_id=pid.value,
            type="latency_sample",
            payload={"dur_ms": 100 + i * 50},
        )
    s = _build_scanner(bus=bus)
    value, err = await s.scan_latency_slo(pid.value)
    assert err is None
    assert value["actual_p95_ms"] is not None
    assert value["actual_p99_ms"] is not None
    assert 0.0 <= value["compliance_rate"] <= 1.0


async def test_scan_latency_slo_no_samples_returns_nulls(pid) -> None:
    s = _build_scanner()
    value, err = await s.scan_latency_slo(pid.value)
    assert err is None
    assert value["actual_p95_ms"] is None
    assert value["actual_p99_ms"] is None


# --- scan_all aggregate ---

async def test_scan_all_returns_eight_keys(pid) -> None:
    s = _build_scanner()
    out = await s.scan_all(pid.value)
    assert set(out.keys()) == {
        "phase",
        "artifacts",
        "wp_status",
        "tool_calls",
        "latency_slo",
        "self_repair_rate",
        "rollback_counter",
        "event_bus",
    }


async def test_scan_all_isolates_per_dim_failure(pid) -> None:
    """l102 timeout should null phase + artifacts but leave other 6 dims fine."""
    s = _build_scanner(l102=L102Stub(_timeout=True))
    out = await s.scan_all(pid.value)
    phase_val, phase_err = out["phase"]
    artifacts_val, artifacts_err = out["artifacts"]
    wp_val, wp_err = out["wp_status"]
    assert phase_val is None and phase_err == SupervisorError.IC_L1_02_TIMEOUT
    assert artifacts_val is None and artifacts_err == SupervisorError.IC_L1_02_TIMEOUT
    assert wp_val is not None and wp_err is None  # L1-03 still OK
