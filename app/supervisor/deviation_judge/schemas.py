"""L2-02 · 4 级偏差判定器 · schemas · INFO/WARN/ERROR/CRITICAL 4 级。

**Brief 简化版（WP04）**：
- 4 级 · INFO(记录) / WARN(→IC-13) / ERROR(→IC-14) / CRITICAL(→IC-15)
- 输入 SupervisorSnapshot · 输出 DeviationVerdict[] · 每维一 verdict
- 纯函数 · 确定性 · 不读 wall-clock（靠 snapshot.captured_at_ms）

注意 level→IC 映射：
- INFO: 无 IC · 仅记录
- WARN: IC-13 push_suggestion(level=WARN)
- ERROR: IC-14 push_rollback_route
- CRITICAL: IC-15 request_hard_halt
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DeviationLevel(str, Enum):
    """4 级偏差分级（brief §3）。"""

    INFO = "INFO"          # 健康波动 · 仅记录
    WARN = "WARN"          # 需关注 · → IC-13
    ERROR = "ERROR"        # 建议降级 · → IC-14
    CRITICAL = "CRITICAL"  # 立即止损 · → IC-15


class DimensionKey(str, Enum):
    """8 维名（对齐 EightDimensionVector 字段）。"""

    PHASE = "phase"
    ARTIFACTS = "artifacts"
    WP_STATUS = "wp_status"
    TOOL_CALLS = "tool_calls"
    LATENCY_SLO = "latency_slo"
    SELF_REPAIR_RATE = "self_repair_rate"
    ROLLBACK_COUNTER = "rollback_counter"
    EVENT_BUS = "event_bus"


class DimensionThreshold(BaseModel):
    """单维 · 阈值配置。WARN / ERROR / CRITICAL 递进。

    阈值语义（YAML 配置）：
    - warn_threshold / error_threshold / critical_threshold 各自是判定 cutoff
    - comparison: 'gt' | 'lt' | 'eq' · 比较方向
    - metric_path: dict 路径 · 如 'value' · 从维 dict 里取数值

    简化版：单一数值阈值判定（不做规则树）。WARN < ERROR < CRITICAL 单调 ·
    违反时 build 期抛 ValueError（见 ThresholdMatrix）。
    """

    model_config = {"frozen": True}

    dimension: DimensionKey
    metric_path: str = Field(..., min_length=1)  # 如 "value" / "p99_ms"
    comparison: str = Field(default="gt")  # gt / lt / eq / ne
    warn_threshold: float | None = None
    error_threshold: float | None = None
    critical_threshold: float | None = None
    absent_is: DeviationLevel = DeviationLevel.INFO  # 维 None 时默认级
    reason_template: str = (
        "dim={dim} path={path} value={value} level={level} threshold={threshold}"
    )

    @field_validator("comparison")
    @classmethod
    def _valid_comparison(cls, v: str) -> str:
        if v not in ("gt", "lt", "eq", "ne"):
            raise ValueError(f"E_THRESHOLD_COMPARISON_INVALID: {v}")
        return v


class DeviationVerdict(BaseModel):
    """单维偏差判定结果。每次 evaluate_deviation 输出 8 条 verdict。

    evidence_refs · 从 snapshot.eight_dim_vector.dim_evidence_refs[dim] 抄过来 ·
    下游 IC-13/14/15 强制要求非空（缺证据维度自动降级 INFO · 不抛）。
    """

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    snapshot_id: str = Field(..., min_length=1)
    dimension: DimensionKey
    level: DeviationLevel
    value: Any | None = None  # 实际采到的数值（可为 dict / float / None）
    threshold: float | None = None  # 命中的阈值（None = INFO 或未配置）
    reason: str = Field(..., min_length=1)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    captured_at_ms: int = Field(..., ge=0)
    verdict_id: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_VERDICT_NO_PROJECT_ID")
        return v


class ThresholdMatrix(BaseModel):
    """8 维阈值矩阵。YAML 加载 · 构造时校验单调（WARN<ERROR<CRITICAL）。"""

    model_config = {"frozen": True}

    version: str = "v1.0"
    dimensions: dict[DimensionKey, DimensionThreshold] = Field(default_factory=dict)

    @field_validator("dimensions")
    @classmethod
    def _monotonic(
        cls,
        v: dict[DimensionKey, DimensionThreshold],
    ) -> dict[DimensionKey, DimensionThreshold]:
        """阈值递进校验 · gt 方向 warn<error<critical · lt 方向 warn>error>critical。"""
        for dim, th in v.items():
            w, e, c = th.warn_threshold, th.error_threshold, th.critical_threshold
            # 仅校验 3 个都非 None 的情形（容许部分配置）
            if w is not None and e is not None and w == e:
                raise ValueError(f"E_THRESHOLD_DUP: {dim.value} warn==error")
            if e is not None and c is not None and e == c:
                raise ValueError(f"E_THRESHOLD_DUP: {dim.value} error==critical")
            if th.comparison == "gt":
                # 越大越严重 · warn < error < critical
                prev = None
                for name, val in (("warn", w), ("error", e), ("critical", c)):
                    if val is None:
                        continue
                    if prev is not None and val <= prev:
                        raise ValueError(
                            f"E_THRESHOLD_NONMONOTONIC: {dim.value} {name}={val} <= prev={prev}"
                        )
                    prev = val
            elif th.comparison == "lt":
                # 越小越严重 · warn > error > critical
                prev = None
                for name, val in (("warn", w), ("error", e), ("critical", c)):
                    if val is None:
                        continue
                    if prev is not None and val >= prev:
                        raise ValueError(
                            f"E_THRESHOLD_NONMONOTONIC: {dim.value} {name}={val} >= prev={prev}"
                        )
                    prev = val
        return v

    def get(self, dim: DimensionKey) -> DimensionThreshold | None:
        return self.dimensions.get(dim)


class DeviationError(str, Enum):
    """L2-02 错误码（简化版 · brief §3）。"""

    NO_PROJECT_ID = "E_VERDICT_NO_PROJECT_ID"
    INVALID_LEVEL = "E_VERDICT_INVALID_LEVEL"
    MATRIX_LOAD_FAIL = "E_THRESHOLD_MATRIX_LOAD_FAIL"
    MATRIX_YAML_CORRUPT = "E_THRESHOLD_MATRIX_YAML_CORRUPT"
    MATRIX_SCHEMA_INVALID = "E_THRESHOLD_MATRIX_SCHEMA_INVALID"
    NONMONOTONIC = "E_THRESHOLD_NONMONOTONIC"
    COMPARISON_INVALID = "E_THRESHOLD_COMPARISON_INVALID"
    METRIC_PATH_MISSING = "E_METRIC_PATH_MISSING"
    SNAPSHOT_INCOMPATIBLE = "E_SNAPSHOT_INCOMPATIBLE"
