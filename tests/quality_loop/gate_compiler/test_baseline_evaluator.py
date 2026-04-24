"""L1-04 · L2-04 · BaselineEvaluator tests · 5 基线判据.

映射:
- brief §职责 · 5 基线判据表
- `app.quality_loop.gate_compiler.baseline_evaluator`

每 1 基线一组 TC (happy + edge + boundary)。
"""
from __future__ import annotations

import pytest

from app.quality_loop.gate_compiler.baseline_evaluator import (
    DEFAULT_REWORK_ABORT_THRESHOLD,
    DEFAULT_SOFT_PASS_THRESHOLD,
    DEFAULT_TOLERATED_FLOOR,
    BaselineEvaluator,
    classify_baseline,
)
from app.quality_loop.gate_compiler.schemas import Baseline, GateAction


class TestBaselineDefaults:
    """阈值默认常量 · 冻结防漂移."""

    def test_TC_L204_BL_001_default_soft_pass_threshold_is_0_8(self) -> None:
        """TC-L204-BL-001 · soft_pass 阈值默认 0.8 (brief §职责)."""
        assert DEFAULT_SOFT_PASS_THRESHOLD == 0.8

    def test_TC_L204_BL_002_default_tolerated_floor_is_0_6(self) -> None:
        """TC-L204-BL-002 · tolerated 下限默认 0.6 (brief §职责)."""
        assert DEFAULT_TOLERATED_FLOOR == 0.6

    def test_TC_L204_BL_003_default_rework_abort_threshold_is_3(self) -> None:
        """TC-L204-BL-003 · 连续 rework abort 阈值默认 3 (brief §职责)."""
        assert DEFAULT_REWORK_ABORT_THRESHOLD == 3


class TestHardPass:
    """hard_pass · 100% hard 通过 · action=ADVANCE."""

    def test_TC_L204_BL_010_hard_pass_all_hard_green_soft_full(self) -> None:
        """TC-L204-BL-010 · hard 3/3 · soft 4/4 · → HARD_PASS · ADVANCE."""
        baseline, action = classify_baseline(
            hard_total=3,
            hard_passed=3,
            soft_total=4,
            soft_passed=4,
            rework_count=0,
        )
        assert baseline == Baseline.HARD_PASS
        assert action == GateAction.ADVANCE

    def test_TC_L204_BL_011_hard_pass_empty_soft_treated_as_hard_pass(self) -> None:
        """TC-L204-BL-011 · hard 2/2 · soft 0/0 (空) · 视为 1.0 通过 → HARD_PASS."""
        baseline, action = classify_baseline(
            hard_total=2,
            hard_passed=2,
            soft_total=0,
            soft_passed=0,
            rework_count=0,
        )
        assert baseline == Baseline.HARD_PASS
        assert action == GateAction.ADVANCE

    def test_TC_L204_BL_012_hard_pass_requires_all_hard_passed(self) -> None:
        """TC-L204-BL-012 · hard 2/3 · 不 hard_pass (跌入 rework)."""
        baseline, _ = classify_baseline(
            hard_total=3,
            hard_passed=2,
            soft_total=5,
            soft_passed=5,
            rework_count=0,
        )
        assert baseline != Baseline.HARD_PASS


class TestSoftPass:
    """soft_pass · hard 全绿 + soft ≥ 80%."""

    def test_TC_L204_BL_020_soft_pass_at_exact_boundary_0_8(self) -> None:
        """TC-L204-BL-020 · hard 全绿 · soft 4/5=0.8 · → SOFT_PASS · ADVANCE."""
        baseline, action = classify_baseline(
            hard_total=2,
            hard_passed=2,
            soft_total=5,
            soft_passed=4,
            rework_count=0,
        )
        assert baseline == Baseline.SOFT_PASS
        assert action == GateAction.ADVANCE

    def test_TC_L204_BL_021_soft_pass_above_0_8(self) -> None:
        """TC-L204-BL-021 · soft 9/10=0.9 · SOFT_PASS."""
        baseline, _ = classify_baseline(
            hard_total=1,
            hard_passed=1,
            soft_total=10,
            soft_passed=9,
            rework_count=0,
        )
        assert baseline == Baseline.SOFT_PASS

    def test_TC_L204_BL_022_not_soft_pass_when_hard_fails(self) -> None:
        """TC-L204-BL-022 · hard 0/1 · soft 满 · 仍 rework · 不 soft_pass."""
        baseline, _ = classify_baseline(
            hard_total=1,
            hard_passed=0,
            soft_total=3,
            soft_passed=3,
            rework_count=0,
        )
        assert baseline == Baseline.REWORK


class TestTolerated:
    """tolerated · hard 全绿 + soft ∈ [60%, 80%) · action=ADVANCE_WITH_WARN."""

    def test_TC_L204_BL_030_tolerated_at_floor_0_6(self) -> None:
        """TC-L204-BL-030 · soft 3/5=0.6 · → TOLERATED · ADVANCE_WITH_WARN."""
        baseline, action = classify_baseline(
            hard_total=2,
            hard_passed=2,
            soft_total=5,
            soft_passed=3,
            rework_count=0,
        )
        assert baseline == Baseline.TOLERATED
        assert action == GateAction.ADVANCE_WITH_WARN

    def test_TC_L204_BL_031_tolerated_below_soft_pass(self) -> None:
        """TC-L204-BL-031 · soft 7/10=0.7 · TOLERATED."""
        baseline, _ = classify_baseline(
            hard_total=3,
            hard_passed=3,
            soft_total=10,
            soft_passed=7,
            rework_count=0,
        )
        assert baseline == Baseline.TOLERATED

    def test_TC_L204_BL_032_not_tolerated_just_below_floor(self) -> None:
        """TC-L204-BL-032 · soft 5/10=0.5 · 跌 rework (不 tolerated)."""
        baseline, _ = classify_baseline(
            hard_total=1,
            hard_passed=1,
            soft_total=10,
            soft_passed=5,
            rework_count=0,
        )
        assert baseline == Baseline.REWORK


class TestRework:
    """rework · hard 失败 / soft < 60% · action=RETRY_S4."""

    def test_TC_L204_BL_040_rework_on_hard_failure(self) -> None:
        """TC-L204-BL-040 · hard 2/3 · soft 满 · → REWORK · RETRY_S4."""
        baseline, action = classify_baseline(
            hard_total=3,
            hard_passed=2,
            soft_total=4,
            soft_passed=4,
            rework_count=0,
        )
        assert baseline == Baseline.REWORK
        assert action == GateAction.RETRY_S4

    def test_TC_L204_BL_041_rework_on_soft_below_floor(self) -> None:
        """TC-L204-BL-041 · hard 全绿 · soft 2/10=0.2 · → REWORK."""
        baseline, _ = classify_baseline(
            hard_total=1,
            hard_passed=1,
            soft_total=10,
            soft_passed=2,
            rework_count=0,
        )
        assert baseline == Baseline.REWORK

    def test_TC_L204_BL_042_rework_at_one_less_than_abort(self) -> None:
        """TC-L204-BL-042 · rework_count=2 (还没到 3) · 仍 REWORK."""
        baseline, action = classify_baseline(
            hard_total=1,
            hard_passed=0,
            soft_total=0,
            soft_passed=0,
            rework_count=2,
        )
        assert baseline == Baseline.REWORK
        assert action == GateAction.RETRY_S4


class TestAbort:
    """abort · 连续 3 次 rework · action=UPGRADE_STAGE_GATE."""

    def test_TC_L204_BL_050_abort_on_third_rework(self) -> None:
        """TC-L204-BL-050 · rework_count=3 · 且本轮也 rework · → ABORT · UPGRADE_STAGE_GATE."""
        baseline, action = classify_baseline(
            hard_total=1,
            hard_passed=0,
            soft_total=0,
            soft_passed=0,
            rework_count=3,
        )
        assert baseline == Baseline.ABORT
        assert action == GateAction.UPGRADE_STAGE_GATE

    def test_TC_L204_BL_051_abort_respects_custom_threshold(self) -> None:
        """TC-L204-BL-051 · 自定义 rework_abort_threshold=5 · rework_count=4 仍 REWORK."""
        baseline, _ = classify_baseline(
            hard_total=1,
            hard_passed=0,
            soft_total=0,
            soft_passed=0,
            rework_count=4,
            rework_abort_threshold=5,
        )
        assert baseline == Baseline.REWORK

    def test_TC_L204_BL_052_abort_only_when_this_round_is_rework(self) -> None:
        """TC-L204-BL-052 · rework_count=3 · 但本轮 hard_pass · 不 abort · 返 HARD_PASS."""
        baseline, _ = classify_baseline(
            hard_total=3,
            hard_passed=3,
            soft_total=0,
            soft_passed=0,
            rework_count=3,
        )
        # 本轮已 hard_pass · rework 链打断 · baseline 返 HARD_PASS
        assert baseline == Baseline.HARD_PASS


class TestInputValidation:
    """输入校验 · 负数 / 越界 · 触发 ValueError."""

    def test_TC_L204_BL_060_negative_hard_total_raises(self) -> None:
        """TC-L204-BL-060 · hard_total<0 · ValueError."""
        with pytest.raises(ValueError, match="E_L204_BL_NEGATIVE"):
            classify_baseline(
                hard_total=-1,
                hard_passed=0,
                soft_total=0,
                soft_passed=0,
                rework_count=0,
            )

    def test_TC_L204_BL_061_hard_passed_exceeds_total_raises(self) -> None:
        """TC-L204-BL-061 · hard_passed>hard_total · ValueError."""
        with pytest.raises(ValueError, match="E_L204_BL_PASSED_EXCEEDS"):
            classify_baseline(
                hard_total=1,
                hard_passed=5,
                soft_total=0,
                soft_passed=0,
                rework_count=0,
            )

    def test_TC_L204_BL_062_soft_passed_exceeds_total_raises(self) -> None:
        """TC-L204-BL-062 · soft_passed>soft_total · ValueError."""
        with pytest.raises(ValueError, match="E_L204_BL_PASSED_EXCEEDS"):
            classify_baseline(
                hard_total=0,
                hard_passed=0,
                soft_total=2,
                soft_passed=3,
                rework_count=0,
            )

    def test_TC_L204_BL_063_negative_rework_count_raises(self) -> None:
        """TC-L204-BL-063 · rework_count<0 · ValueError."""
        with pytest.raises(ValueError, match="E_L204_BL_NEGATIVE"):
            classify_baseline(
                hard_total=1,
                hard_passed=1,
                soft_total=0,
                soft_passed=0,
                rework_count=-1,
            )


class TestBaselineEvaluatorFromEvaluated:
    """BaselineEvaluator · 从 EvaluatedDoD 计算 baseline."""

    def test_TC_L204_BL_070_from_evaluated_dod_hard_pass(self) -> None:
        """TC-L204-BL-070 · EvaluatedDoD hard 2/2 · soft 3/3 · → HARD_PASS."""
        from app.quality_loop.gate_compiler.dod_adapter import (
            EvaluatedDoD,
            EvaluatedExpression,
        )
        from app.quality_loop.dod_compiler import DoDExpressionKind

        evaluated = EvaluatedDoD(
            dod_set_id="set-1",
            dod_hash="hash-1",
            project_id="p1",
            hard=[
                EvaluatedExpression(
                    expr_id=f"h{i}",
                    kind=DoDExpressionKind.HARD,
                    passed=True,
                    reason="ok",
                )
                for i in range(2)
            ],
            soft=[
                EvaluatedExpression(
                    expr_id=f"s{i}",
                    kind=DoDExpressionKind.SOFT,
                    passed=True,
                    reason="ok",
                )
                for i in range(3)
            ],
            missing=[],
        )
        evaluator = BaselineEvaluator()
        baseline, action = evaluator.evaluate(evaluated, rework_count=0)
        assert baseline == Baseline.HARD_PASS
        assert action == GateAction.ADVANCE

    def test_TC_L204_BL_071_from_evaluated_dod_tolerated(self) -> None:
        """TC-L204-BL-071 · hard 1/1 · soft 3/5=0.6 · → TOLERATED."""
        from app.quality_loop.gate_compiler.dod_adapter import (
            EvaluatedDoD,
            EvaluatedExpression,
        )
        from app.quality_loop.dod_compiler import DoDExpressionKind

        evaluated = EvaluatedDoD(
            dod_set_id="set-1",
            dod_hash="hash-1",
            project_id="p1",
            hard=[
                EvaluatedExpression(
                    expr_id="h1",
                    kind=DoDExpressionKind.HARD,
                    passed=True,
                    reason="ok",
                ),
            ],
            soft=[
                EvaluatedExpression(
                    expr_id=f"s{i}",
                    kind=DoDExpressionKind.SOFT,
                    passed=(i < 3),
                    reason="ok" if i < 3 else "miss",
                )
                for i in range(5)
            ],
            missing=[],
        )
        evaluator = BaselineEvaluator()
        baseline, _ = evaluator.evaluate(evaluated, rework_count=0)
        assert baseline == Baseline.TOLERATED

    def test_TC_L204_BL_072_custom_thresholds(self) -> None:
        """TC-L204-BL-072 · 自定义 soft_pass=0.9 · 0.85 不再 soft_pass · TOLERATED."""
        from app.quality_loop.gate_compiler.dod_adapter import (
            EvaluatedDoD,
            EvaluatedExpression,
        )
        from app.quality_loop.dod_compiler import DoDExpressionKind

        evaluated = EvaluatedDoD(
            dod_set_id="set-1",
            dod_hash="hash-1",
            project_id="p1",
            hard=[
                EvaluatedExpression(
                    expr_id="h1",
                    kind=DoDExpressionKind.HARD,
                    passed=True,
                    reason="ok",
                ),
            ],
            soft=[
                EvaluatedExpression(
                    expr_id=f"s{i}",
                    kind=DoDExpressionKind.SOFT,
                    passed=(i < 17),
                    reason="ok" if i < 17 else "miss",
                )
                for i in range(20)
            ],
            missing=[],
        )
        evaluator = BaselineEvaluator(soft_pass_threshold=0.9, tolerated_floor=0.6)
        baseline, _ = evaluator.evaluate(evaluated, rework_count=0)
        # 17/20 = 0.85 < 0.9 但 ≥ 0.6 → TOLERATED
        assert baseline == Baseline.TOLERATED
