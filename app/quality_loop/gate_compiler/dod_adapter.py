"""L1-04 · L2-04 · DoD Adapter · 消费 WP01 `dod_compiler` 产出的 `CompiledDoD`.

职责：
1. 从 WP01 `CompiledDoD` 聚合根中提取 `hard` / `soft` 表达式集合。
2. 对每个 `DoDExpression` · 调 WP01 `DoDEvaluator.eval_expression` 求值（注入 metric 作
   data_sources_snapshot · 每个表达式一次性求值）。
3. 汇总成 `EvaluatedDoD` · 供 `BaselineEvaluator` 消费。

**真实 import · 无 mock**：`from app.quality_loop.dod_compiler import ...`

**并发策略**：WP01 `DoDEvaluator` 是 thread-safe · 本 adapter 同步顺序调用（单 WP
评估一次性完成 · 不并发）。错误累积 · 不 short-circuit（缺 evidence 作为
`MissingEvidence` 汇总给 Verdict）。
"""
from __future__ import annotations

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
    - `reason`        · WP01 返回的文字原因（≥ 10 字符）
    - `missing_keys`  · 若 WP01 eval 因缺字段失败 · 记录 missing keys
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr_id: str = Field(..., min_length=1)
    kind: DoDExpressionKind
    passed: bool
    reason: str = Field(..., min_length=1)
    missing_keys: list[str] = Field(default_factory=list)


class EvaluatedDoD(BaseModel):
    """聚合根 VO · 一次 WP 评估的 DoD 集合结果。

    - `hard`          · hard 表达式结果列表（`EvaluatedExpression.kind == HARD`）
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
        adapter = DoDAdapter(evaluator=DoDEvaluator(registry))
        evaluated = adapter.evaluate(compiled_dod, metric_snapshot, project_id="p1")

    - 不修改 WP01 内部状态。
    - 不并发；按 hard → soft 顺序评估。
    - metric 表达式（kind=METRIC）跳过（metric 维度由 MetricSampler 独立管理 · 本
      L2-04 MVP 不在 gate 评估中直接评估 metric 表达式）。
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
            compiled: WP01 产出的 `CompiledDoD`（必须带 set_id + dod_hash）。
            metric_snapshot: metric 名 → 值的字典 · 传给 WP01 `EvalCommand.data_sources_snapshot`。
            project_id: PM-14 顶层 · 若与 `compiled.project_id` 不一致 · 抛
                `DoDAdapterError`。

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
            if result is None:
                missing.append(
                    MissingEvidence(
                        expr_id=expr.expr_id,
                        missing_key=_infer_missing_key(expr, metric_snapshot),
                        hint=f"hard expression '{expr.expr_id}' requires metric key(s) not in snapshot",
                    ),
                )
                # 缺 evidence 记为 failed · 进入 hard_passed 计数
                hard_results.append(
                    EvaluatedExpression(
                        expr_id=expr.expr_id,
                        kind=DoDExpressionKind.HARD,
                        passed=False,
                        reason="missing evidence for hard predicate evaluation",
                        missing_keys=[_infer_missing_key(expr, metric_snapshot)],
                    ),
                )
            else:
                hard_results.append(result)

        for expr in compiled.soft:
            result = self._eval_one(expr, metric_snapshot, project_id)
            if result is None:
                missing.append(
                    MissingEvidence(
                        expr_id=expr.expr_id,
                        missing_key=_infer_missing_key(expr, metric_snapshot),
                        hint=f"soft expression '{expr.expr_id}' requires metric key(s) not in snapshot",
                    ),
                )
                soft_results.append(
                    EvaluatedExpression(
                        expr_id=expr.expr_id,
                        kind=DoDExpressionKind.SOFT,
                        passed=False,
                        reason="missing evidence for soft predicate evaluation",
                        missing_keys=[_infer_missing_key(expr, metric_snapshot)],
                    ),
                )
            else:
                soft_results.append(result)

        # metric 维度在 gate 评估里跳过（MVP · metric 归 MetricSampler 管）
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
    ) -> EvaluatedExpression | None:
        """调 WP01 evaluator · 映射错误为 None（→ missing_evidence 通路）。

        返 None：evaluator 因 missing key 失败（WP01 抛 `DoDEvalError`）。
        返 EvaluatedExpression：成功（含 passed=True/False + reason）。
        """
        cmd = EvalCommand(
            command_id=f"gate-eval-{expr.expr_id}",
            project_id=project_id,
            expr_id=expr.expr_id,
            data_sources_snapshot=dict(metric_snapshot),
            caller=self.caller,
        )
        try:
            result: EvalResult = self.evaluator.eval_expression(cmd, compiled_expr=expr)
        except DoDEvalError:
            return None
        except Exception as exc:  # noqa: BLE001 — 防御：任何 WP01 内部异常转 adapter error
            raise DoDAdapterError(f"E_L204_EVAL_UNEXPECTED: {exc!s}") from exc

        return EvaluatedExpression(
            expr_id=expr.expr_id,
            kind=expr.kind,
            passed=bool(result.pass_),
            reason=result.reason or "eval completed",
            missing_keys=[],
        )


def _synth_hash(compiled: CompiledDoD) -> str:
    """compiled.dod_hash 可能空（WP01 schema 默认 ""）· 用 set_id 合成稳定替代 hash。

    不从真 hash 计算 · 仅作 GateVerdict 幂等 key 的 fallback。
    """
    return f"fallback-{compiled.set_id}"


def _infer_missing_key(expr: DoDExpression, snapshot: dict[str, Any]) -> str:
    """从表达式文本粗略推断 missing 的 metric key.

    非精确（WP01 已有更精确的 predicate_eval）· 本函数仅在 adapter 兜底时给出人类可读的提示。
    返回首个不在 snapshot 中的 key · 若推断不出 · 返 "unknown"。
    """
    candidates = [token for token in _tokenize(expr.expression_text) if token.isidentifier()]
    for tok in candidates:
        if tok not in snapshot and tok not in _PY_LITERALS:
            return tok
    return "unknown"


def _tokenize(text: str) -> list[str]:
    """拆 DoD 表达式文本 · 只保留 identifier-like 子串。"""
    out: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    return out


_PY_LITERALS: frozenset[str] = frozenset(
    ["True", "False", "None", "and", "or", "not", "in"],
)


__all__ = [
    "DoDAdapter",
    "DoDAdapterError",
    "EvaluatedDoD",
    "EvaluatedExpression",
]
