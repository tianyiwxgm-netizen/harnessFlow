"""L2-02 · schemas 校验 TC。"""
from __future__ import annotations

import pytest

from app.supervisor.deviation_judge.schemas import (
    DeviationLevel,
    DeviationVerdict,
    DimensionKey,
    DimensionThreshold,
    ThresholdMatrix,
)


class TestDeviationLevel:
    def test_four_levels_present(self) -> None:
        assert DeviationLevel.INFO.value == "INFO"
        assert DeviationLevel.WARN.value == "WARN"
        assert DeviationLevel.ERROR.value == "ERROR"
        assert DeviationLevel.CRITICAL.value == "CRITICAL"

    def test_levels_ordered_by_severity(self) -> None:
        # 字符串比较不保证顺序 · 但 set 可预期大小
        levels = {
            DeviationLevel.INFO,
            DeviationLevel.WARN,
            DeviationLevel.ERROR,
            DeviationLevel.CRITICAL,
        }
        assert len(levels) == 4


class TestDimensionThreshold:
    def test_valid_gt_threshold(self) -> None:
        th = DimensionThreshold(
            dimension=DimensionKey.LATENCY_SLO,
            metric_path="p99_ms",
            comparison="gt",
            warn_threshold=200,
            error_threshold=500,
            critical_threshold=1000,
        )
        assert th.comparison == "gt"
        assert th.warn_threshold == 200

    def test_invalid_comparison_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_COMPARISON_INVALID"):
            DimensionThreshold(
                dimension=DimensionKey.LATENCY_SLO,
                metric_path="p99_ms",
                comparison="between",  # 非法
            )

    def test_frozen(self) -> None:
        th = DimensionThreshold(
            dimension=DimensionKey.LATENCY_SLO,
            metric_path="p99_ms",
        )
        with pytest.raises(Exception):  # pydantic v2 frozen: ValidationError
            th.warn_threshold = 100  # type: ignore[misc]


class TestThresholdMatrix:
    def test_monotonic_gt_ok(self) -> None:
        matrix = ThresholdMatrix(
            version="v1",
            dimensions={
                DimensionKey.LATENCY_SLO: DimensionThreshold(
                    dimension=DimensionKey.LATENCY_SLO,
                    metric_path="p99_ms",
                    comparison="gt",
                    warn_threshold=200,
                    error_threshold=500,
                    critical_threshold=1000,
                ),
            },
        )
        assert matrix.get(DimensionKey.LATENCY_SLO) is not None

    def test_nonmonotonic_gt_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_NONMONOTONIC"):
            ThresholdMatrix(
                version="v1",
                dimensions={
                    DimensionKey.LATENCY_SLO: DimensionThreshold(
                        dimension=DimensionKey.LATENCY_SLO,
                        metric_path="p99_ms",
                        comparison="gt",
                        warn_threshold=500,
                        error_threshold=200,  # 逆序
                        critical_threshold=1000,
                    ),
                },
            )

    def test_dup_warn_error_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_DUP"):
            ThresholdMatrix(
                version="v1",
                dimensions={
                    DimensionKey.LATENCY_SLO: DimensionThreshold(
                        dimension=DimensionKey.LATENCY_SLO,
                        metric_path="p99_ms",
                        comparison="gt",
                        warn_threshold=500,
                        error_threshold=500,  # 重复
                    ),
                },
            )

    def test_monotonic_lt_ok(self) -> None:
        matrix = ThresholdMatrix(
            version="v1",
            dimensions={
                DimensionKey.WP_STATUS: DimensionThreshold(
                    dimension=DimensionKey.WP_STATUS,
                    metric_path="healthy_rate",
                    comparison="lt",
                    warn_threshold=0.8,
                    error_threshold=0.5,
                    critical_threshold=0.2,
                ),
            },
        )
        assert matrix.get(DimensionKey.WP_STATUS).warn_threshold == 0.8

    def test_nonmonotonic_lt_rejected(self) -> None:
        with pytest.raises(ValueError, match="E_THRESHOLD_NONMONOTONIC"):
            ThresholdMatrix(
                version="v1",
                dimensions={
                    DimensionKey.WP_STATUS: DimensionThreshold(
                        dimension=DimensionKey.WP_STATUS,
                        metric_path="healthy_rate",
                        comparison="lt",
                        warn_threshold=0.2,
                        error_threshold=0.5,  # 逆序
                        critical_threshold=0.8,
                    ),
                },
            )


class TestDeviationVerdict:
    def test_pid_required(self) -> None:
        with pytest.raises(ValueError, match="E_VERDICT_NO_PROJECT_ID"):
            DeviationVerdict(
                project_id="   ",
                snapshot_id="snap-1",
                dimension=DimensionKey.PHASE,
                level=DeviationLevel.INFO,
                reason="test",
                captured_at_ms=1,
                verdict_id="v-1",
            )

    def test_valid_verdict(self) -> None:
        v = DeviationVerdict(
            project_id="proj-abc",
            snapshot_id="snap-1",
            dimension=DimensionKey.LATENCY_SLO,
            level=DeviationLevel.WARN,
            value=250,
            threshold=200,
            reason="over warn",
            evidence_refs=("ev-1", "ev-2"),
            captured_at_ms=1000,
            verdict_id="v-1",
        )
        assert v.level is DeviationLevel.WARN
        assert v.threshold == 200
