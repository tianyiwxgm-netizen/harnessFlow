"""L1-04 · L2-04 · 质量 Gate 编译器 schemas.

锚点：
- docs/3-1-Solution-Technical/L1-04-Quality Loop/L2-04-质量 Gate 编译器+验收 Checklist.md §7
- 3-3 Monitoring-Controlling quality-standards / dod-specs
- 用户任务 brief §职责：5 基线判据（hard_pass / soft_pass / tolerated / rework / abort）

**核心类型**：
- `Baseline`        · 5 基线枚举（StrEnum）
- `GateAction`      · 下游 target_stage 建议（Quality Loop 路由输入）
- `VerdictReason`   · GateVerdict 产生原因的结构化 VO
- `MissingEvidence` · hard/soft 缺 metric 的描述
- `GateVerdict`     · 裁决结果 · frozen Pydantic

**PM-14 约束**：所有顶层 VO 首字段 `project_id`；跨 pid 合成禁止。
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GateCompilerError(Exception):
    """L2-04 Gate 编译器统一错误基类。

    子错误在各模块（`DoDAdapterError` / `MetricSamplerError`）定义 · 不在 schemas 强耦合。
    """


class Baseline(StrEnum):
    """5 基线裁决（brief §职责）。

    字符串值（StrEnum）便于 JSON 序列化与 log 友好。
    """

    HARD_PASS = "hard_pass"
    SOFT_PASS = "soft_pass"
    TOLERATED = "tolerated"
    REWORK = "rework"
    ABORT = "abort"


class GateAction(StrEnum):
    """下游路由建议 · 供 Quality Loop 主入口使用。

    - `ADVANCE`            · 继续推进（hard_pass / soft_pass）。
    - `ADVANCE_WITH_WARN`  · 推进但记录警告（tolerated）。
    - `RETRY_S4`           · 返 S4 重执行（rework）。
    - `UPGRADE_STAGE_GATE` · 升级到 Stage Gate · main supervisor 接管（abort）。
    """

    ADVANCE = "ADVANCE"
    ADVANCE_WITH_WARN = "ADVANCE_WITH_WARN"
    RETRY_S4 = "RETRY_S4"
    UPGRADE_STAGE_GATE = "UPGRADE_STAGE_GATE"


class MissingEvidence(BaseModel):
    """缺失的 metric / evidence 描述。

    场景：DoD 表达式引用 `coverage`，但 metric_sample 未提供 → `missing_key=coverage`。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expr_id: str = Field(..., min_length=1)
    missing_key: str = Field(..., min_length=1)
    hint: str = Field(default="", max_length=400)


class VerdictReason(BaseModel):
    """GateVerdict 产生原因（结构化 · 可 marshal 到 IC-09 append_event）。

    字段：
    - `hard_total` / `hard_passed`     · hard 表达式统计
    - `soft_total` / `soft_passed`     · soft 表达式统计
    - `soft_ratio`                     · soft 通过率（0.0-1.0）
    - `rework_count`                   · 触发本次 verdict 前的累计 rework 次数
    - `missing_evidence`               · 无法评估的表达式列表
    - `text`                           · human-readable 总结 · 首行供 checklist 展示
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hard_total: int = Field(..., ge=0)
    hard_passed: int = Field(..., ge=0)
    soft_total: int = Field(..., ge=0)
    soft_passed: int = Field(..., ge=0)
    soft_ratio: float = Field(..., ge=0.0, le=1.0)
    rework_count: int = Field(..., ge=0)
    missing_evidence: list[MissingEvidence] = Field(default_factory=list)
    text: str = Field(..., min_length=1, max_length=2000)

    @field_validator("soft_ratio")
    @classmethod
    def _round_ratio(cls, v: float) -> float:
        """保留 4 位小数 · 防止 log 对比漂移。"""
        return round(v, 4)


class GateVerdict(BaseModel):
    """L2-04 Gate 裁决 VO · frozen 不可变。

    对下游（L2-05 S4 / L2-07 rollback_router / L1-01 主环）输出：
    - `baseline`       · 5 基线之一
    - `action`         · 路由建议（GateAction）
    - `verdict_id`     · 幂等 key · 基于 dod_hash + metric_sample_hash 计算
    - `dod_hash`       · 来自 WP01 `CompiledDoD.dod_hash`
    - `metric_hash`    · 来自 `MetricSample.sample_hash`
    - `reason`         · `VerdictReason` 结构化
    - `project_id`     · PM-14 顶层
    - `wp_id`          · 本次评估针对的 WP
    - `dod_set_id`     · 关联 `CompiledDoD.set_id`
    - `evaluated_at`   · ISO 8601 UTC
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    wp_id: str | None = None
    dod_set_id: str = Field(..., min_length=1)
    dod_hash: str = Field(..., min_length=1)
    metric_hash: str = Field(..., min_length=1)
    baseline: Baseline
    action: GateAction
    reason: VerdictReason
    evaluated_at: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_L204_NO_PROJECT_ID")
        return v


__all__ = [
    "Baseline",
    "GateAction",
    "GateCompilerError",
    "GateVerdict",
    "MissingEvidence",
    "VerdictReason",
]
