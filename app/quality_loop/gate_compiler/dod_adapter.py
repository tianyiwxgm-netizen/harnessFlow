"""L1-04 · L2-04 · DoD Adapter · 消费 WP01 `dod_compiler` 产出的 `CompiledDoD`.

职责：
1. 从 WP01 `CompiledDoD` 聚合根中提取 `hard` / `soft` 表达式集合。
2. 对每个 `DoDExpression` · 调 WP01 `DoDEvaluator.eval_expression`（表达式已由
   `DoDExpressionCompiler` 注册到 compiler._expressions · evaluator 通过 expr_id 查找）。
3. 注入 metric snapshot（嵌套格式 · 与 WP01 `WHITELISTED_DATA_SOURCE_KEYS` 对齐:
   `{"coverage": {...}, "test_result": {...}, "lint": {...}, "perf": {...}, ...}`）。
4. 汇总成 `EvaluatedDoD` · 供 `BaselineEvaluator` 消费。

**真实 import · 无 mock**：`from app.quality_loop.dod_compiler import ...`

**错误累积不 short-circuit**：缺 evidence / eval 失败 → `MissingEvidence` + passed=False。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.quality_loop.dod_compiler import (
    CompiledDoD,
    DoDEvaluator,
    DoDExpression,
    DoDExpressionKind,
    EvalCommand,
    EvalResult,
)
from app.quality_loop.dod_compiler.errors import DoDEvalError
from app.quality_loop.dod_compiler.schemas import EvalCaller
from app.quality_loop.gate_compiler.schemas import (
    GateCompilerError,
    MissingEvidence,
)


class DoDAdapterError(GateCompilerError):
    """DoD adapter 层错误（WP01 evaluator 调用失败 / 数据源缺失聚合异常）。"""


class EvaluatedExpression(BaseModel):
    """单 DoD 表达式评估结果 · adapter 层 VO（frozen）。

    映射 WP01 `EvalResult`:
    - `expr_id`       · DoD 表达式 ID
    - `kind`          · hard / soft / metric（仅 hard+soft 参与 baseline 判据 · metric
                         单独走 MetricSampler）
    - `passed`        · 是否通过（WP01 `pass_`）
    - `reason`        · WP01 返回的文字原因（≥ 1 字符 · 放松 WP01 的 10 字符约束用于
                         adapter 层兜底 "missing evidence" 等短 reason）
    - `missing_keys`  · 若 WP01 eval 因缺字段失败 · 记录 missing keys
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr_id: str = Field(..., min_length=1)
    kind: DoDExpressionKind
    passed: bool
    reason: str = Field(..., min_length=1, max_length=2000)
    missing_keys: list[str] = Field(default_factory=list)


class EvaluatedDoD(BaseModel):
    """聚合根 VO · 一次 WP 评估的 DoD 集合结果。

    - `hard`          · hard 表达式结果列表
    - `soft`          · soft 表达式结果列表
    - `missing`       · 跨集合的 missing_evidence 聚合
    - `dod_set_id`    · 来自 `CompiledDoD.set_id`
    - `dod_hash`      · 来自 `CompiledDoD.dod_hash`
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dod_set_id: str = Field(..., min_length=1)
    dod_hash: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    hard: list[EvaluatedExpression] = Field(default_factory=list)
    soft: list[EvaluatedExpression] = Field(default_factory=list)
    missing: list[MissingEvidence] = Field(default_factory=list)

    @property
    def hard_total(self) -> int:
        return len(self.hard)

    @property
    def hard_passed(self) -> int:
        return sum(1 for e in self.hard if e.passed)

    @property
    def hard_all_passed(self) -> bool:
        """True 当且仅当 hard_total == hard_passed（含空集 True）。"""
        return self.hard_total == self.hard_passed

    @property
    def soft_total(self) -> int:
        return len(self.soft)

    @property
    def soft_passed(self) -> int:
        return sum(1 for e in self.soft if e.passed)

    @property
    def soft_ratio(self) -> float:
        """soft 通过率 · 空集记 1.0（视为 100% 通过）。"""
        if self.soft_total == 0:
            return 1.0
        return self.soft_passed / self.soft_total


@dataclass
class DoDAdapter:
    """WP01 `DoDEvaluator` → L2-04 `EvaluatedDoD` 适配器。

    用法：
        compiler = DoDExpressionCompiler(...)
        compile_result = compiler.compile_batch(cmd)  # 注册 expr 到 compiler._expressions
        evaluator = DoDEvaluator(compiler)
        adapter = DoDAdapter(evaluator=evaluator)
        evaluated = adapter.evaluate(
            compile_result.compiled,
            metric_snapshot={"coverage": {"line_rate": 0.85}},
            project_id="p1",
        )

    - 不修改 WP01 内部状态。
    - 不并发；按 hard → soft 顺序评估。
    - metric 表达式（kind=METRIC）跳过 · 归 MetricSampler 管。
    """

    evaluator: DoDEvaluator
    caller: EvalCaller = EvalCaller.L2_04_GATE_CONFIG_CHECK

    def evaluate(
        self,
        compiled: CompiledDoD,
        metric_snapshot: dict[str, Any],
        *,
        project_id: str,
    ) -> EvaluatedDoD:
        """对 `CompiledDoD` 求值 · 返 `EvaluatedDoD`.

        Args:
            compiled: WP01 产出的 `CompiledDoD`（必须带 set_id）。
            metric_snapshot: 嵌套 data source 字典 · 传给 WP01
                `EvalCommand.data_sources_snapshot`。格式:
                `{"coverage": {...}, "test_result": {...}, "lint": {...}, ...}`
                key 必须在 WP01 `WHITELISTED_DATA_SOURCE_KEYS` 内。
            project_id: PM-14 顶层。必须与 `compiled.project_id` 一致。

        Returns:
            `EvaluatedDoD`（聚合 hard/soft 结果 + missing 清单）。

        Raises:
            DoDAdapterError: project_id 不一致 · 或 WP01 eval 返非预期异常。
        """
        if compiled.project_id != project_id:
            raise DoDAdapterError(
                f"E_L204_PID_MISMATCH: compiled.project_id={compiled.project_id!r} "
                f"!= project_id={project_id!r}",
            )

        hard_results: list[EvaluatedExpression] = []
        soft_results: list[EvaluatedExpression] = []
        missing: list[MissingEvidence] = []

        for expr in compiled.hard:
            result = self._eval_one(expr, metric_snapshot, project_id)
            hard_results.append(result)
            if result.missing_keys:
                missing.append(
                    MissingEvidence(
                        expr_id=expr.expr_id,
                        missing_key=result.missing_keys[0],
                        hint=f"hard expression '{expr.expr_id}' eval failed: {result.reason}",
                    ),
                )

        for expr in compiled.soft:
            result = self._eval_one(expr, metric_snapshot, project_id)
            soft_results.append(result)
            if result.missing_keys:
                missing.append(
                    MissingEvidence(
                        expr_id=expr.expr_id,
                        missing_key=result.missing_keys[0],
                        hint=f"soft expression '{expr.expr_id}' eval failed: {result.reason}",
                    ),
                )

        # metric 维度在 gate 评估里跳过（MVP · 归 MetricSampler 管）
        return EvaluatedDoD(
            dod_set_id=compiled.set_id,
            dod_hash=compiled.dod_hash or _synth_hash(compiled),
            project_id=project_id,
            hard=hard_results,
            soft=soft_results,
            missing=missing,
        )

    # ------------------------ internals ------------------------ #

    def _eval_one(
        self,
        expr: DoDExpression,
        metric_snapshot: dict[str, Any],
        project_id: str,
    ) -> EvaluatedExpression:
        """调 WP01 evaluator · 映射错误为 missing_keys 通路。

        WP01 `DoDEvaluator.eval_expression(cmd)` 只接 `EvalCommand`（expr_id 查找 compiler
        内部 registry）。失败时(DoDEvalError)返 passed=False + missing_keys=[错误分类]。
        """
        cmd = EvalCommand(
            command_id=f"gate-eval-{expr.expr_id}-{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            expr_id=expr.expr_id,
            data_sources_snapshot=dict(metric_snapshot),
            caller=self.caller,
        )
        try:
            result: EvalResult = self.evaluator.eval_expression(cmd)
        except DoDEvalError as exc:
            return EvaluatedExpression(
                expr_id=expr.expr_id,
                kind=expr.kind,
                passed=False,
                reason=f"eval failed: {exc!s}"[:1900],
                missing_keys=[type(exc).__name__],
            )
        except Exception as exc:  # noqa: BLE001 — 防御：任何 WP01 内部异常转 adapter error
            raise DoDAdapterError(f"E_L204_EVAL_UNEXPECTED: {exc!s}") from exc

        return EvaluatedExpression(
            expr_id=expr.expr_id,
            kind=expr.kind,
            passed=bool(result.pass_),
            reason=(result.reason or "eval completed")[:1900],
            missing_keys=[],
        )


def _synth_hash(compiled: CompiledDoD) -> str:
    """compiled.dod_hash 可能空（WP01 schema 默认 ""）· 用 set_id 合成稳定替代 hash。

    不从真 hash 计算 · 仅作 GateVerdict 幂等 key 的 fallback。
    """
    return f"fallback-{compiled.set_id}"


__all__ = [
    "DoDAdapter",
    "DoDAdapterError",
    "EvaluatedDoD",
    "EvaluatedExpression",
]
