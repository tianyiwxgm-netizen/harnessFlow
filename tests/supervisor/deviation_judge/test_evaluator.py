"""L2-02 · evaluator.evaluate_deviation TC · 纯函数 + 确定性。"""
from __future__ import annotations

from typing import Any

import pytest

from app.supervisor.deviation_judge import (
    LEVEL_TO_IC,
    DeviationLevel,
    DimensionKey,
    default_matrix,
    evaluate_deviation,
    filter_actionable,
    load_matrix_from_dict,
)
from app.supervisor.dim_collector.schemas import (
    DegradationLevel,
    EightDimensionVector,
    SupervisorSnapshot,
    TriggerSource,
)


# ==================== Helpers ====================


def _make_snap(
    *,
    pid: str = "proj-abc",
    vector: EightDimensionVector | None = None,
    captured_at_ms: int = 1000,
    snapshot_id: str = "snap-abcd1234abcd",
) -> SupervisorSnapshot:
    if vector is None:
        vector = EightDimensionVector()
    return SupervisorSnapshot(
        project_id=pid,
        snapshot_id=snapshot_id,
        captured_at_ms=captured_at_ms,
        trigger=TriggerSource.TICK,
        eight_dim_vector=vector,
        degradation_level=DegradationLevel.FULL,
        degradation_reason_map={},
        evidence_refs=(),
        collection_latency_ms=10,
    )


# ==================== Positive ====================


class TestEvaluate8Dims:
    def test_all_none_vector_8_info(self) -> None:
        snap = _make_snap()
        matrix = default_matrix()
        verdicts = evaluate_deviation(snap, matrix)
        assert len(verdicts) == 8
        # 默认 absent_is=INFO · 所有 verdict level==INFO
        assert all(v.level is DeviationLevel.INFO for v in verdicts)

    def test_fixed_dim_order(self) -> None:
        snap = _make_snap()
        matrix = default_matrix()
        verdicts = evaluate_deviation(snap, matrix)
        dims = [v.dimension for v in verdicts]
        assert dims == [
            DimensionKey.PHASE,
            DimensionKey.ARTIFACTS,
            DimensionKey.WP_STATUS,
            DimensionKey.TOOL_CALLS,
            DimensionKey.LATENCY_SLO,
            DimensionKey.SELF_REPAIR_RATE,
            DimensionKey.ROLLBACK_COUNTER,
            DimensionKey.EVENT_BUS,
        ]

    def test_latency_warn_triggers(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 250})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.WARN
        assert latency_v.threshold == 200

    def test_latency_error_triggers(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 600})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.ERROR
        assert latency_v.threshold == 500

    def test_latency_critical_triggers(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 5000})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.CRITICAL

    def test_latency_below_warn_info(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 50})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.INFO

    def test_metric_path_missing_info_fallback(self) -> None:
        # latency_slo 有值但没有 p99_ms 字段
        vec = EightDimensionVector(latency_slo={"wrong_key": 999})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.INFO
        assert "missing" in latency_v.reason

    def test_dim_none_uses_absent_is(self) -> None:
        # 构造自定义 matrix · absent_is=WARN
        matrix = load_matrix_from_dict(
            {
                "dimensions": {
                    "latency_slo": {
                        "metric_path": "p99_ms",
                        "comparison": "gt",
                        "absent_is": "WARN",
                    }
                }
            }
        )
        snap = _make_snap()
        verdicts = evaluate_deviation(snap, matrix)
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.level is DeviationLevel.WARN

    def test_evidence_refs_propagated(self) -> None:
        vec = EightDimensionVector(
            latency_slo={"p99_ms": 100},
            dim_evidence_refs={"latency_slo": ("ev-1", "ev-2")},
        )
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        latency_v = next(v for v in verdicts if v.dimension is DimensionKey.LATENCY_SLO)
        assert latency_v.evidence_refs == ("ev-1", "ev-2")

    def test_captured_at_ms_propagated(self) -> None:
        snap = _make_snap(captured_at_ms=5555)
        verdicts = evaluate_deviation(snap, default_matrix())
        assert all(v.captured_at_ms == 5555 for v in verdicts)


# ==================== Determinism ====================


class TestDeterminism:
    def test_same_snapshot_same_verdicts(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 300})
        snap = _make_snap(vector=vec)
        matrix = default_matrix()
        v1 = evaluate_deviation(snap, matrix)
        v2 = evaluate_deviation(snap, matrix)
        assert [v.verdict_id for v in v1] == [v.verdict_id for v in v2]
        assert [v.level for v in v1] == [v.level for v in v2]

    def test_different_snap_different_ids(self) -> None:
        snap1 = _make_snap(snapshot_id="snap-aaaaaaaaaaaa")
        snap2 = _make_snap(snapshot_id="snap-bbbbbbbbbbbb")
        v1 = evaluate_deviation(snap1, default_matrix())
        v2 = evaluate_deviation(snap2, default_matrix())
        # snapshot_id 不同 · verdict_id 应不同
        ids1 = {v.verdict_id for v in v1}
        ids2 = {v.verdict_id for v in v2}
        assert not ids1 & ids2


# ==================== Comparison modes ====================


class TestComparisonModes:
    def test_comparison_lt(self) -> None:
        matrix = load_matrix_from_dict(
            {
                "dimensions": {
                    "wp_status": {
                        "metric_path": "healthy_rate",
                        "comparison": "lt",
                        "warn_threshold": 0.8,
                        "error_threshold": 0.5,
                        "critical_threshold": 0.2,
                    }
                }
            }
        )
        # value = 0.3 · <= warn(0.8) + <= error(0.5) · 应 ERROR（不到 critical 0.2）
        vec = EightDimensionVector(wp_status={"healthy_rate": 0.3})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, matrix)
        wp_v = next(v for v in verdicts if v.dimension is DimensionKey.WP_STATUS)
        assert wp_v.level is DeviationLevel.ERROR

    def test_comparison_eq(self) -> None:
        matrix = load_matrix_from_dict(
            {
                "dimensions": {
                    "wp_status": {
                        "metric_path": "fail_count",
                        "comparison": "eq",
                        "warn_threshold": 1,
                        "error_threshold": 2,
                        "critical_threshold": 3,
                    }
                }
            }
        )
        vec = EightDimensionVector(wp_status={"fail_count": 2})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, matrix)
        wp_v = next(v for v in verdicts if v.dimension is DimensionKey.WP_STATUS)
        assert wp_v.level is DeviationLevel.ERROR

    def test_comparison_ne(self) -> None:
        matrix = load_matrix_from_dict(
            {
                "dimensions": {
                    "event_bus": {
                        "metric_path": "lag_ms",
                        "comparison": "ne",
                        "warn_threshold": 0,
                    }
                }
            }
        )
        # value=50 != 0 · WARN 命中（无更严重层）
        vec = EightDimensionVector(event_bus={"lag_ms": 50})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, matrix)
        eb_v = next(v for v in verdicts if v.dimension is DimensionKey.EVENT_BUS)
        assert eb_v.level is DeviationLevel.WARN


# ==================== filter_actionable + LEVEL_TO_IC ====================


class TestActionableFilter:
    def test_filter_drops_info(self) -> None:
        vec = EightDimensionVector(latency_slo={"p99_ms": 300})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        actionable = filter_actionable(verdicts)
        # 应只剩 latency_slo=WARN 一条
        assert len(actionable) == 1
        assert actionable[0].dimension is DimensionKey.LATENCY_SLO

    def test_level_to_ic_map(self) -> None:
        assert LEVEL_TO_IC[DeviationLevel.INFO] is None
        assert LEVEL_TO_IC[DeviationLevel.WARN] == "IC-13"
        assert LEVEL_TO_IC[DeviationLevel.ERROR] == "IC-14"
        assert LEVEL_TO_IC[DeviationLevel.CRITICAL] == "IC-15"


# ==================== Multi-dim at same time ====================


class TestMultiDim:
    def test_three_dims_different_levels(self) -> None:
        vec = EightDimensionVector(
            latency_slo={"p99_ms": 5000},  # CRITICAL
            self_repair_rate={"rate": 0.4},  # WARN
            rollback_counter={"count_24h": 7},  # ERROR
        )
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, default_matrix())
        by_dim: dict[DimensionKey, Any] = {v.dimension: v for v in verdicts}
        assert by_dim[DimensionKey.LATENCY_SLO].level is DeviationLevel.CRITICAL
        assert by_dim[DimensionKey.SELF_REPAIR_RATE].level is DeviationLevel.WARN
        assert by_dim[DimensionKey.ROLLBACK_COUNTER].level is DeviationLevel.ERROR


# ==================== Snapshot no-threshold fallback ====================


class TestNoThresholdConfig:
    def test_no_matrix_config_info_fallback(self) -> None:
        # 极简 matrix · 只配 1 维
        matrix = load_matrix_from_dict(
            {"dimensions": {"latency_slo": {"metric_path": "p99_ms"}}}
        )
        # wp_status 维有值 · 但 matrix 里没配 · 预期 INFO
        vec = EightDimensionVector(wp_status={"fail_count": 100})
        snap = _make_snap(vector=vec)
        verdicts = evaluate_deviation(snap, matrix)
        wp_v = next(v for v in verdicts if v.dimension is DimensionKey.WP_STATUS)
        assert wp_v.level is DeviationLevel.INFO
        assert "no_threshold_config" in wp_v.reason
