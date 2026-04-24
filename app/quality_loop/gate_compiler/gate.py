"""L1-04 · L2-04 · GateCompiler · Facade · evaluate_gate(dod, metric) → GateVerdict.

**职责**（brief · gate.py 主入口）：
1. 编排 `DoDAdapter` → `BaselineEvaluator` → `ChecklistCompiler` 三件套。
2. 通过 `RewordCounter` 追踪 (project_id, dod_set_id) 连续 rework 次数 ·
   触发 abort 时叠加（见 baseline_evaluator.classify_baseline）。
3. 产 `GateVerdict`（5 基线 + action + reason + 幂等 verdict_id）。
4. 幂等：同 `(dod_hash, metric_sample_hash, rework_count)` → 同 `verdict_id`。

**与 S5 / L1-01 主环的对接点**：
- 输入 `EvaluateGateCommand`（含 compiled + metrics + project_id + wp_id）
- 输出 `GateEvaluateResult`（verdict + checklist + evaluated_dod）
"""
from __future__ import annotations

import hashlib
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.quality_loop.dod_compiler import CompiledDoD
from app.quality_loop.gate_compiler.baseline_evaluator import (
    DEFAULT_REWORK_ABORT_THRESHOLD,
    DEFAULT_SOFT_PASS_THRESHOLD,
    DEFAULT_TOLERATED_FLOOR,
    BaselineEvaluator,
)
from app.quality_loop.gate_compiler.checklist_compiler import (
    AcceptanceChecklist,
    ChecklistCompiler,
)
from app.quality_loop.gate_compiler.dod_adapter import (
    DoDAdapter,
    EvaluatedDoD,
)
from app.quality_loop.gate_compiler.metric_sampler import (
    MetricSample,
    MetricSampler,
)
from app.quality_loop.gate_compiler.schemas import (
    Baseline,
    GateVerdict,
    VerdictReason,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class EvaluateGateCommand(BaseModel):
    """gate 主入口入参 · frozen VO。"""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    project_id: str = Field(..., min_length=1)
    compiled: CompiledDoD
    metrics: dict[str, Any] = Field(default_factory=dict)
    wp_id: str | None = None


class GateEvaluateResult(BaseModel):
    """gate 主入口出参 · frozen VO。

    含 `verdict` + `checklist` + `evaluated` 三个 artifact · 方便调用方同步消费。
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    verdict: GateVerdict
    checklist: AcceptanceChecklist
    evaluated: EvaluatedDoD
    sample: MetricSample


class RewordCounter:
    """(project_id, dod_set_id) → 连续 rework 次数 · thread-safe in-memory map.

    语义:
    - `observe(baseline)`: 若 baseline==REWORK → +1；否则清零(包括 ABORT)。
    - `get(...)`: 返当前计数（新 key 返 0）。
    """

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = defaultdict(int)
        self._lock = threading.Lock()

    def get(self, *, project_id: str, dod_set_id: str) -> int:
        with self._lock:
            return self._counts.get((project_id, dod_set_id), 0)

    def observe(self, *, project_id: str, dod_set_id: str, baseline: Baseline) -> int:
        """观测本轮 baseline · 更新计数 · 返回更新后的计数。"""
        key = (project_id, dod_set_id)
        with self._lock:
            if baseline == Baseline.REWORK:
                self._counts[key] = self._counts.get(key, 0) + 1
            else:
                # HARD_PASS / SOFT_PASS / TOLERATED / ABORT 都清零（ABORT 后
                # 意味升级到 Stage Gate · 之后的流程不再累计）
                self._counts[key] = 0
            return self._counts[key]


@dataclass
class GateCompiler:
    """Gate 编排 Facade · 组合 adapter / evaluator / checklist / sampler / counter.

    用法:
        compiler = DoDExpressionCompiler(...)
        compiler.compile_batch(cmd)  # 注册 expr
        evaluator = DoDEvaluator(compiler)
        gate = GateCompiler(
            dod_adapter=DoDAdapter(evaluator=evaluator),
            metric_sampler=MetricSampler(),
            baseline_evaluator=BaselineEvaluator(),
            checklist_compiler=ChecklistCompiler(),
            rework_counter=RewordCounter(),
        )
        result = gate.evaluate_gate(EvaluateGateCommand(...))
    """

    dod_adapter: DoDAdapter
    metric_sampler: MetricSampler
    rework_counter: RewordCounter
    baseline_evaluator: BaselineEvaluator = field(default_factory=BaselineEvaluator)
    checklist_compiler: ChecklistCompiler = field(default_factory=ChecklistCompiler)

    def evaluate_gate(self, cmd: EvaluateGateCommand) -> GateEvaluateResult:
        """编排一次 gate 评估 · 产 `GateVerdict` + `AcceptanceChecklist`.

        Raises:
            DoDAdapterError: project_id 不匹配等
            MetricSamplerError: metric 格式问题
        """
        # 1. 规范化 metric
        sample = self.metric_sampler.sample(
            project_id=cmd.project_id,
            metrics=cmd.metrics,
            wp_id=cmd.wp_id,
        )

        # 2. 适配 WP01 · 评估 DoD
        evaluated = self.dod_adapter.evaluate(
            cmd.compiled,
            metric_snapshot=sample.values,
            project_id=cmd.project_id,
        )

        # 3. 取历史 rework_count（本轮尚未 observe）
        rework_count = self.rework_counter.get(
            project_id=cmd.project_id,
            dod_set_id=evaluated.dod_set_id,
        )

        # 4. 5 基线判据
        baseline, action = self.baseline_evaluator.evaluate(
            evaluated,
            rework_count=rework_count,
        )

        # 5. observe 更新 counter（REWORK +1 · 其它清零）
        # 注意：ABORT 也要清零 · 防止升级后再触发
        self.rework_counter.observe(
            project_id=cmd.project_id,
            dod_set_id=evaluated.dod_set_id,
            baseline=baseline,
        )

        # 6. 产 checklist
        checklist = self.checklist_compiler.compile(
            compiled=cmd.compiled,
            evaluated=evaluated,
        )

        # 7. 产 VerdictReason（结构化 + text summary）
        reason = self._build_reason(evaluated, rework_count=rework_count)

        # 8. 产 GateVerdict（幂等 verdict_id 基于 dod_hash + metric_hash + rework_count）
        verdict_id = self._compute_verdict_id(
            dod_hash=evaluated.dod_hash,
            metric_hash=sample.sample_hash,
            rework_count=rework_count,
            project_id=cmd.project_id,
        )
        verdict = GateVerdict(
            verdict_id=verdict_id,
            project_id=cmd.project_id,
            wp_id=cmd.wp_id,
            dod_set_id=evaluated.dod_set_id,
            dod_hash=evaluated.dod_hash,
            metric_hash=sample.sample_hash,
            baseline=baseline,
            action=action,
            reason=reason,
            evaluated_at=_now_iso(),
        )

        return GateEvaluateResult(
            verdict=verdict,
            checklist=checklist,
            evaluated=evaluated,
            sample=sample,
        )

    # ------------------------ internals ------------------------ #

    def _build_reason(
        self,
        evaluated: EvaluatedDoD,
        *,
        rework_count: int,
    ) -> VerdictReason:
        text_parts: list[str] = [
            f"hard={evaluated.hard_passed}/{evaluated.hard_total}",
            f"soft={evaluated.soft_passed}/{evaluated.soft_total}",
            f"soft_ratio={evaluated.soft_ratio:.2f}",
            f"rework_count={rework_count}",
        ]
        if evaluated.missing:
            text_parts.append(f"missing={len(evaluated.missing)}")
        text = " · ".join(text_parts)
        return VerdictReason(
            hard_total=evaluated.hard_total,
            hard_passed=evaluated.hard_passed,
            soft_total=evaluated.soft_total,
            soft_passed=evaluated.soft_passed,
            soft_ratio=evaluated.soft_ratio,
            rework_count=rework_count,
            missing_evidence=list(evaluated.missing),
            text=text,
        )

    def _compute_verdict_id(
        self,
        *,
        dod_hash: str,
        metric_hash: str,
        rework_count: int,
        project_id: str,
    ) -> str:
        """幂等 verdict_id · sha256 前 24 hex · 带 verdict- 前缀。"""
        material = f"{project_id}|{dod_hash}|{metric_hash}|rw={rework_count}"
        h = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
        return f"verdict-{h}"


__all__ = [
    "EvaluateGateCommand",
    "GateCompiler",
    "GateEvaluateResult",
    "RewordCounter",
]
