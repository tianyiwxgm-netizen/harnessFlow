"""L2-07 schemas · IC-14 消费端 · 严格对齐 Dev-ζ 生产端。

**对齐基线**：`app/supervisor/event_sender/schemas.py`（Dev-ζ 已 merged）
- `FailVerdict`：`FAIL_L1 / FAIL_L2 / FAIL_L3 / FAIL_L4`（不含 PASS · PASS 不走 IC-14）
- `TargetStage`：`S3 / S4 / S5 / UPGRADE_TO_L1_01`
- `NewWpState`：`retry_s3 / retry_s4 / retry_s5 / upgraded_to_l1_01`
- `PushRollbackRouteCommand`：消费端 payload
- `PushRollbackRouteAck`：ack 响应（幂等回包）

本模块**重导出**上述生产端枚举（避免双份定义漂移），并定义本 L2-07 消费端
独有的分类 / 决策结果 schema。

**severity 4 级**：
- `INFO_SUGG` — L1 信息建议 · 记录不回退（不走 IC-14 路径）
- `WARN`     — L2 轻度 · FAIL_L1 · stage 内 retry（→ S3）
- `FAIL`     — L3 中度 · FAIL_L2/L3 · 回上一 stage（→ S4 / S5）
- `CRITICAL` — L4 深度 · FAIL_L4 或同级 ≥ 3 · 升级 L1-01

**错误码**：复用 Dev-ζ `SenderError`（消费端不单列一份）。
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# 重导出 Dev-ζ 生产端枚举 · 严格对齐 · 禁本地再定义
from app.supervisor.event_sender.schemas import (
    FailVerdict,
    NewWpState,
    PushRollbackRouteAck,
    PushRollbackRouteCommand,
    RouteEvidence,
    TargetStage,
)

__all__ = [
    # re-export · 对齐 Dev-ζ
    "FailVerdict",
    "NewWpState",
    "PushRollbackRouteAck",
    "PushRollbackRouteCommand",
    "RouteEvidence",
    "TargetStage",
    # L2-07 消费端独有
    "RollbackSeverity",
    "RollbackVerdict",
    "RouteDecision",
]


class RollbackSeverity(StrEnum):
    """4 级严重度 · verdict_classifier 输出。

    - `INFO_SUGG` · L1 信息建议 · 记录不回退（不走 IC-14 · 本 L2 不接到）。
    - `WARN`     · L2 轻度回退 · stage 内 retry 当前 WP。
    - `FAIL`     · L3 中度回退 · 回退到上一 stage。
    - `CRITICAL` · L4 深度回退 · 回 S1/S2 · 重新 Planning（UPGRADE_TO_L1_01）。
    """

    INFO_SUGG = "INFO_SUGG"
    WARN = "WARN"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"


class RollbackVerdict(BaseModel):
    """L2-07 分类后的内部 verdict · 含原始 verdict + severity 分级。

    frozen 不可变 · 供 stage_mapper / executor 链路传递。
    """

    model_config = {"frozen": True}

    verdict: FailVerdict
    severity: RollbackSeverity
    wp_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    level_count: int = Field(..., ge=1, description="同 (wp,verdict) 连续失败次数")


class RouteDecision(BaseModel):
    """stage_mapper 的决策输出 · 供 executor 消费。

    - `target_stage`：将要路由到的 stage（严格用 Dev-ζ `TargetStage` 枚举）。
    - `escalated`：是否因同级 ≥ 3 触发升级（override 常规映射到 UPGRADE_TO_L1_01）。
    - `new_wp_state`：预期 WP 的新状态（Dev-ζ `NewWpState`）。
    """

    model_config = {"frozen": True}

    target_stage: TargetStage
    new_wp_state: NewWpState
    severity: RollbackSeverity
    escalated: bool = False
    route_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    level_count: int = Field(..., ge=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_ROUTE_NO_PROJECT_ID")  # 对齐 Dev-ζ SenderError
        return v
