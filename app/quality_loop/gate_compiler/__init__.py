"""L1-04 · L2-04 · 质量 Gate 编译器 + 验收 Checklist.

**定位**：Quality Loop 的 Gate 裁决层 · 消费 DoD AST(WP01 `dod_compiler`)+
metric 样本(外部 S4/S5 注入) · 产出 5 基线 GateVerdict + 验收 Checklist。

**5 基线判据（3-3 quality-standards · §2 核心清单）**：

| baseline | 判据 | target_stage 建议 |
|:---|:---|:---|
| `hard_pass`  | 100% hard 表达式通过          | ADVANCE |
| `soft_pass`  | hard 全绿 & soft ≥ 80%        | ADVANCE |
| `tolerated`  | hard 全绿 & soft ∈ [60%, 80%) | ADVANCE_WITH_WARN |
| `rework`     | hard 失败 或 soft < 60%       | RETRY_S4 |
| `abort`      | 连续 3 次 `rework`            | UPGRADE_TO_STAGE_GATE |

**对外暴露**：
- `GateCompiler`            · Facade · `evaluate_gate(dod, metric) → GateVerdict`
- `BaselineEvaluator`       · 纯函数 · 5 基线判据
- `MetricSampler`           · 外部 metric → `MetricSample`
- `DoDAdapter`              · 适配 WP01 `CompiledDoD`
- `ChecklistCompiler`       · 产 human-readable `AcceptanceChecklist`
- schemas（`GateVerdict` / `Baseline` / `AcceptanceChecklist` …）

**约束**：
- 依赖 WP01 `app.quality_loop.dod_compiler`（真实 import · 无 mock）
- PM-14：所有 VO 带 `project_id`；跨 pid 拒绝。
- 幂等：同 `dod_hash + metric_sample_hash` → 同 `GateVerdict`。
- 配置：连续 rework 阈值默认 3 次（可注入）。
"""
from __future__ import annotations

from app.quality_loop.gate_compiler.baseline_evaluator import (
    BaselineEvaluator,
    DEFAULT_REWORK_ABORT_THRESHOLD,
    DEFAULT_SOFT_PASS_THRESHOLD,
    DEFAULT_TOLERATED_FLOOR,
    classify_baseline,
)
from app.quality_loop.gate_compiler.checklist_compiler import (
    AcceptanceChecklist,
    ChecklistCompiler,
    ChecklistItem,
)
from app.quality_loop.gate_compiler.dod_adapter import (
    DoDAdapter,
    DoDAdapterError,
    EvaluatedDoD,
    EvaluatedExpression,
)
from app.quality_loop.gate_compiler.gate import (
    EvaluateGateCommand,
    GateCompiler,
    RewordCounter,
)
from app.quality_loop.gate_compiler.metric_sampler import (
    MetricSample,
    MetricSampler,
    MetricSamplerError,
)
from app.quality_loop.gate_compiler.schemas import (
    Baseline,
    GateAction,
    GateCompilerError,
    GateVerdict,
    MissingEvidence,
    VerdictReason,
)

__all__ = [
    "AcceptanceChecklist",
    "Baseline",
    "BaselineEvaluator",
    "ChecklistCompiler",
    "ChecklistItem",
    "DEFAULT_REWORK_ABORT_THRESHOLD",
    "DEFAULT_SOFT_PASS_THRESHOLD",
    "DEFAULT_TOLERATED_FLOOR",
    "DoDAdapter",
    "DoDAdapterError",
    "EvaluateGateCommand",
    "EvaluatedDoD",
    "EvaluatedExpression",
    "GateAction",
    "GateCompiler",
    "GateCompilerError",
    "GateVerdict",
    "MetricSample",
    "MetricSampler",
    "MetricSamplerError",
    "MissingEvidence",
    "RewordCounter",
    "VerdictReason",
    "classify_baseline",
]
