"""L2-01 输出 schema · pydantic v2 frozen · PM-14 pid 非空。

EightDimensionVector：8 维可独立 None · 每维失败单独降级。
SupervisorSnapshot：包一层 meta（trigger / degradation / evidence_refs）。
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TriggerSource(str, Enum):
    """采集触发来源。"""

    TICK = "TICK"                # 30s 周期
    POST_TOOL_USE = "POST_TOOL_USE"  # hook · 500ms 硬锁
    ON_DEMAND = "ON_DEMAND"      # UI / CLI 查询
    STATE_CHANGED = "STATE_CHANGED"  # 关键状态变更即时


class DegradationLevel(str, Enum):
    """本次采集整体的退化等级。"""

    FULL = "FULL"                      # 8 维全 present
    FULL_FAST = "FULL_FAST"            # 8 维有值 · 但 6 维来自 cache
    SOME_DIM_MISSING = "SOME_DIM_MISSING"  # 1-7 维缺
    LAST_KNOWN_GOOD = "LAST_KNOWN_GOOD"    # 使用 LKG fallback
    STALE_WARNING = "STALE_WARNING"        # 全缺 · LKG 也过期


class EightDimensionVector(BaseModel):
    """8 维度状态向量。每维独立 None-able · 采集失败即 None。

    dim_evidence_refs（WP01-P1 补丁 · tech-design §2.2 + PRD §8.4）：
    - 每维值必须可追溯到源事件 id
    - key ∈ 8 维名 · value 为 tuple[str, ...]（可空 · 表示该维无证据或失败）
    - 总审计索引 SupervisorSnapshot.evidence_refs 是所有维的 union（去重）
    """

    model_config = {"frozen": True}

    phase: str | None = None
    artifacts: dict[str, Any] | None = None
    wp_status: dict[str, Any] | None = None
    tool_calls: dict[str, Any] | None = None
    latency_slo: dict[str, Any] | None = None
    self_repair_rate: dict[str, Any] | None = None
    rollback_counter: dict[str, Any] | None = None
    event_bus: dict[str, Any] | None = None
    dim_evidence_refs: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @property
    def present_count(self) -> int:
        """返回 non-None 维度数 · 用于 degradation_level 判别。"""
        return sum(
            1
            for f in (
                self.phase,
                self.artifacts,
                self.wp_status,
                self.tool_calls,
                self.latency_slo,
                self.self_repair_rate,
                self.rollback_counter,
                self.event_bus,
            )
            if f is not None
        )


class SupervisorSnapshot(BaseModel):
    """完整 8 维快照 · L2-01 三入口统一输出。

    PM-14：project_id 非空 · 所有下游消费者可据此 pid 分片存储。
    vector_schema_version：锁定 v1.0 · 版本漂移 → E_SCHEMA_VERSION_MISMATCH。
    """

    model_config = {"frozen": True}

    project_id: str = Field(..., min_length=1)
    snapshot_id: str
    captured_at_ms: int
    trigger: TriggerSource
    eight_dim_vector: EightDimensionVector
    degradation_level: DegradationLevel
    degradation_reason_map: dict[str, str]
    evidence_refs: tuple[str, ...]
    collection_latency_ms: int
    vector_schema_version: str = "v1.0"
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("project_id is required (PM-14)")
        return v
