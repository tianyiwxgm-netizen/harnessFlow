"""Schemas 契约：EightDimensionVector + SupervisorSnapshot · TriggerSource / DegradationLevel。

锁定 vector_schema_version = v1.0 · PM-14 pid 非空 · 8 维可独立 None。
"""
from __future__ import annotations

import pytest

from app.supervisor.dim_collector.schemas import (
    DegradationLevel,
    EightDimensionVector,
    SupervisorSnapshot,
    TriggerSource,
)


def test_vector_all_none_is_valid() -> None:
    v = EightDimensionVector()
    assert v.phase is None
    assert v.artifacts is None
    assert v.wp_status is None
    assert v.present_count == 0


def test_vector_present_count_reflects_populated() -> None:
    v = EightDimensionVector(phase="S3", wp_status={"total": 10})
    assert v.present_count == 2


def test_vector_accepts_full_payload() -> None:
    v = EightDimensionVector(
        phase="S3",
        artifacts={"completeness_pct": 80.0, "missing": []},
        wp_status={
            "total": 10,
            "completed": 3,
            "in_progress": 2,
            "blocked": 0,
            "completion_pct": 30.0,
        },
        tool_calls={
            "last_tool_name": "git",
            "red_line_candidate": False,
            "last_n_calls": [],
        },
        latency_slo={
            "slo_target_ms": 2000,
            "actual_p95_ms": 800,
            "actual_p99_ms": 1200,
            "compliance_rate": 0.97,
        },
        self_repair_rate={"attempts": 5, "successes": 4, "failures": 1, "rate": 0.8},
        rollback_counter={"count": 0, "by_reason": {}},
        event_bus={
            "event_count_last_30s": 12,
            "event_lag_ms": 15,
            "event_types": ["decision"],
        },
    )
    assert v.phase == "S3"
    assert v.present_count == 8


def test_snapshot_requires_project_id_pm14() -> None:
    with pytest.raises(ValueError):
        SupervisorSnapshot(
            project_id="",
            snapshot_id="snap-1",
            captured_at_ms=0,
            trigger=TriggerSource.TICK,
            eight_dim_vector=EightDimensionVector(),
            degradation_level=DegradationLevel.FULL,
            degradation_reason_map={},
            evidence_refs=(),
            collection_latency_ms=0,
        )


def test_snapshot_locked_schema_version() -> None:
    s = SupervisorSnapshot(
        project_id="proj-a",
        snapshot_id="snap-1",
        captured_at_ms=1,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=0,
    )
    assert s.vector_schema_version == "v1.0"


def test_snapshot_frozen_after_construction() -> None:
    s = SupervisorSnapshot(
        project_id="proj-a",
        snapshot_id="snap-1",
        captured_at_ms=1,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=0,
    )
    # pydantic v2 frozen=True should block direct mutation
    with pytest.raises((AttributeError, Exception)):
        s.project_id = "other"  # type: ignore[misc]


def test_degradation_level_enum_values() -> None:
    assert {d.value for d in DegradationLevel} == {
        "FULL",
        "FULL_FAST",
        "SOME_DIM_MISSING",
        "LAST_KNOWN_GOOD",
        "STALE_WARNING",
    }


def test_trigger_source_enum_values() -> None:
    assert {t.value for t in TriggerSource} == {
        "TICK",
        "POST_TOOL_USE",
        "ON_DEMAND",
        "STATE_CHANGED",
    }


def test_snapshot_evidence_refs_is_tuple() -> None:
    s = SupervisorSnapshot(
        project_id="proj-a",
        snapshot_id="snap-1",
        captured_at_ms=1,
        trigger=TriggerSource.TICK,
        eight_dim_vector=EightDimensionVector(),
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=("ev-1", "ev-2"),
        collection_latency_ms=5,
    )
    assert s.evidence_refs == ("ev-1", "ev-2")
