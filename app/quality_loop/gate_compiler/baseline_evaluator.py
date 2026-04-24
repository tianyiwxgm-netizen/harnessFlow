"""L1-04 · L2-04 · BaselineEvaluator · 5 基线判据纯函数 + 薄 OO 封装.

brief §职责 · 5 基线判据表:

| baseline | 判据 | target_stage 建议 |
|:---|:---|:---|
| `hard_pass`  | hard 100% 通过                | ADVANCE |
| `soft_pass`  | hard 全绿 & soft ≥ 80%        | ADVANCE |
| `tolerated`  | hard 全绿 & soft ∈ [60%, 80%) | ADVANCE_WITH_WARN |
| `rework`     | hard 失败 或 soft < 60%       | RETRY_S4 |
| `abort`      | 连续 ≥ 3 次 rework (且本轮也 rework) | UPGRADE_STAGE_GATE |

**纯函数 `classify_baseline`**：无副作用 · 同样入参 → 同 baseline+action。
**`BaselineEvaluator`**：薄 OO 包装（便于注入自定义阈值 · 给 GateCompiler 用）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.quality_loop.gate_compiler.schemas import Baseline, GateAction

if TYPE_CHECKING:
    from app.quality_loop.gate_compiler.dod_adapter import EvaluatedDoD


DEFAULT_SOFT_PASS_THRESHOLD: float = 0.8
"""soft_pass 下限（brief §职责 · ≥ 80%）。"""

DEFAULT_TOLERATED_FLOOR: float = 0.6
"""tolerated 下限（brief §职责 · ≥ 60% & < 80%）。"""

DEFAULT_REWORK_ABORT_THRESHOLD: int = 3
"""连续 rework 到达此阈值且本轮仍 rework → abort（brief §职责）。"""


def classify_baseline(
    *,
    hard_total: int,
    hard_passed: int,
    soft_total: int,
    soft_passed: int,
    rework_count: int,
    soft_pass_threshold: float = DEFAULT_SOFT_PASS_THRESHOLD,
    tolerated_floor: float = DEFAULT_TOLERATED_FLOOR,
    rework_abort_threshold: int = DEFAULT_REWORK_ABORT_THRESHOLD,
) -> tuple[Baseline, GateAction]:
    """5 基线判据纯函数 · 不可变入参 → baseline + action。

    Args:
        hard_total: hard 表达式总数（≥ 0）。
        hard_passed: hard 通过数（0 ≤ ... ≤ hard_total）。
        soft_total: soft 表达式总数（≥ 0）。
        soft_passed: soft 通过数（0 ≤ ... ≤ soft_total）。
        rework_count: 历史累计 rework 次数（≥ 0）。不含本轮。
        soft_pass_threshold: soft_pass 下限（默认 0.8）。
        tolerated_floor: tolerated 下限（默认 0.6）。
        rework_abort_threshold: 触发 abort 的连续 rework 次数（默认 3）。

    Returns:
        (Baseline, GateAction)。action 固定映射:
        - HARD_PASS / SOFT_PASS → ADVANCE
        - TOLERATED             → ADVANCE_WITH_WARN
        - REWORK                → RETRY_S4
        - ABORT                 → UPGRADE_STAGE_GATE

    Raises:
        ValueError: 输入非法（负数 · passed>total · 阈值越界）。
    """
    _validate_non_negative(hard_total, "hard_total")
    _validate_non_negative(hard_passed, "hard_passed")
    _validate_non_negative(soft_total, "soft_total")
    _validate_non_negative(soft_passed, "soft_passed")
    _validate_non_negative(rework_count, "rework_count")

    if hard_passed > hard_total:
        raise ValueError(
            f"E_L204_BL_PASSED_EXCEEDS: hard_passed={hard_passed} > hard_total={hard_total}",
        )
    if soft_passed > soft_total:
        raise ValueError(
            f"E_L204_BL_PASSED_EXCEEDS: soft_passed={soft_passed} > soft_total={soft_total}",
        )
    if not 0.0 < soft_pass_threshold <= 1.0:
        raise ValueError(
            f"E_L204_BL_THRESHOLD_INVALID: soft_pass_threshold={soft_pass_threshold}",
        )
    if not 0.0 < tolerated_floor <= soft_pass_threshold:
        raise ValueError(
            f"E_L204_BL_THRESHOLD_INVALID: tolerated_floor={tolerated_floor} "
            f"not in (0, soft_pass_threshold={soft_pass_threshold}]",
        )
    if rework_abort_threshold < 1:
        raise ValueError(
            f"E_L204_BL_THRESHOLD_INVALID: rework_abort_threshold={rework_abort_threshold} < 1",
        )

    hard_all_passed = (hard_total == hard_passed)
    soft_ratio = 1.0 if soft_total == 0 else soft_passed / soft_total

    # 判断本轮 baseline（不考虑历史 rework 累积 · 那是 abort 的叠加条件）
    if hard_all_passed and soft_ratio >= soft_pass_threshold:
        if soft_total == 0 or soft_ratio == 1.0:
            this_round = Baseline.HARD_PASS
        elif soft_ratio >= soft_pass_threshold:
            this_round = Baseline.SOFT_PASS
        else:  # pragma: no cover — 不可达
            this_round = Baseline.SOFT_PASS
    elif hard_all_passed and tolerated_floor <= soft_ratio < soft_pass_threshold:
        this_round = Baseline.TOLERATED
    else:
        # hard 不全绿 · 或 soft < tolerated_floor
        this_round = Baseline.REWORK

    # abort 叠加：历史 rework_count ≥ threshold 且本轮 rework
    if this_round == Baseline.REWORK and rework_count >= rework_abort_threshold:
        return Baseline.ABORT, GateAction.UPGRADE_STAGE_GATE

    return this_round, _action_for(this_round)


def _action_for(baseline: Baseline) -> GateAction:
    """baseline → action 固定映射。"""
    if baseline == Baseline.HARD_PASS or baseline == Baseline.SOFT_PASS:
        return GateAction.ADVANCE
    if baseline == Baseline.TOLERATED:
        return GateAction.ADVANCE_WITH_WARN
    if baseline == Baseline.REWORK:
        return GateAction.RETRY_S4
    return GateAction.UPGRADE_STAGE_GATE


def _validate_non_negative(n: int, name: str) -> None:
    if n < 0:
        raise ValueError(f"E_L204_BL_NEGATIVE: {name}={n} must be ≥ 0")


@dataclass(frozen=True)
class BaselineEvaluator:
    """OO 包装 · 持久化阈值注入 · 从 EvaluatedDoD 计算 baseline。

    用法:
        evaluator = BaselineEvaluator()
        baseline, action = evaluator.evaluate(evaluated_dod, rework_count=2)
    """

    soft_pass_threshold: float = DEFAULT_SOFT_PASS_THRESHOLD
    tolerated_floor: float = DEFAULT_TOLERATED_FLOOR
    rework_abort_threshold: int = DEFAULT_REWORK_ABORT_THRESHOLD

    def evaluate(
        self,
        evaluated: "EvaluatedDoD",
        *,
        rework_count: int,
    ) -> tuple[Baseline, GateAction]:
        """从 `EvaluatedDoD` 聚合计数 · 调 `classify_baseline`。"""
        return classify_baseline(
            hard_total=evaluated.hard_total,
            hard_passed=evaluated.hard_passed,
            soft_total=evaluated.soft_total,
            soft_passed=evaluated.soft_passed,
            rework_count=rework_count,
            soft_pass_threshold=self.soft_pass_threshold,
            tolerated_floor=self.tolerated_floor,
            rework_abort_threshold=self.rework_abort_threshold,
        )


__all__ = [
    "BaselineEvaluator",
    "DEFAULT_REWORK_ABORT_THRESHOLD",
    "DEFAULT_SOFT_PASS_THRESHOLD",
    "DEFAULT_TOLERATED_FLOOR",
    "classify_baseline",
]
