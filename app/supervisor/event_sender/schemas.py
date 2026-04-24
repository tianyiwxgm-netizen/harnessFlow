"""L2-04 event_sender · IC-13 / IC-14 / IC-15 三 IC 的 payload schema。

按 ic-contracts.md §3.13 / §3.14 / §3.15 逐字段落地 · pydantic v2 frozen · PM-14 pid 非空。

**主会话仲裁约束**（2026-04-23-Dev-ζ-4-corrections.md）：
- IC-13 → L1-01 · push_suggestion · fire-and-forget
- IC-14 → L1-04 · push_rollback_route · 幂等 by (wp_id, route_id)
- IC-15 → L1-01 · request_hard_halt · 阻塞式 ≤100ms 硬约束

不按 Dev-ζ impl plan §A 的误读（C-1/C-2 已驳回）。
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# IC-13 · push_suggestion
# ==============================================================================


class SuggestionLevel(str, Enum):
    """§3.13.2 · 3 级建议 · BLOCK 级不走本 IC（走 IC-15）。"""

    INFO = "INFO"
    SUGG = "SUGG"
    WARN = "WARN"


class SuggestionPriority(str, Enum):
    INFO = "P2"  # alias
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class PushSuggestionCommand(BaseModel):
    """§3.13.2 · push_suggestion_command。

    level=BLOCK 会被拒绝（走 IC-15）· content < 10 字符拒绝 · observation_refs minItems=1。
    """

    model_config = {"frozen": True}

    suggestion_id: str = Field(..., pattern=r"^sugg-[A-Za-z0-9_-]{3,}")
    project_id: str = Field(..., min_length=1)
    level: SuggestionLevel
    content: str = Field(..., min_length=10)
    observation_refs: tuple[str, ...] = Field(..., min_length=1)
    priority: SuggestionPriority = SuggestionPriority.P2
    require_ack_tick_delta: int | None = None
    ts: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_SUGG_NO_PROJECT_ID")
        return v


class PushSuggestionAck(BaseModel):
    """§3.13.3 · push_suggestion_ack。"""

    model_config = {"frozen": True}

    suggestion_id: str
    enqueued: bool
    queue_len: int
    evicted_suggestion_id: str | None = None


# ==============================================================================
# IC-14 · push_rollback_route
# ==============================================================================


class FailVerdict(str, Enum):
    """§3.14.2 · Quality Loop 4 档 FAIL。"""

    FAIL_L1 = "FAIL_L1"
    FAIL_L2 = "FAIL_L2"
    FAIL_L3 = "FAIL_L3"
    FAIL_L4 = "FAIL_L4"


class TargetStage(str, Enum):
    """§3.14.2 · verdict → target_stage 映射枚举。"""

    S3 = "S3"
    S4 = "S4"
    S5 = "S5"
    UPGRADE_TO_L1_01 = "UPGRADE_TO_L1-01"


class RouteEvidence(BaseModel):
    model_config = {"frozen": True}
    verifier_report_id: str
    decision_id: str | None = None


class PushRollbackRouteCommand(BaseModel):
    """§3.14.2 · push_rollback_route_command。

    幂等 key = (wp_id, route_id) · 重复推同 route_id 返回已 applied 的 ack。
    """

    model_config = {"frozen": True}

    route_id: str = Field(..., pattern=r"^route-[A-Za-z0-9_-]{3,}")
    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., pattern=r"^wp-[A-Za-z0-9_-]{2,}")
    verdict: FailVerdict
    target_stage: TargetStage
    level_count: int = Field(..., ge=1)
    evidence: RouteEvidence
    ts: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_ROUTE_NO_PROJECT_ID")
        return v


class NewWpState(str, Enum):
    RETRY_S3 = "retry_s3"
    RETRY_S4 = "retry_s4"
    RETRY_S5 = "retry_s5"
    UPGRADED_TO_L1_01 = "upgraded_to_l1_01"


class PushRollbackRouteAck(BaseModel):
    """§3.14.3 · push_rollback_route_ack。"""

    model_config = {"frozen": True}

    route_id: str
    applied: bool
    new_wp_state: NewWpState
    escalated: bool = False
    ts: str


# ==============================================================================
# IC-15 · request_hard_halt
# ==============================================================================


class HardHaltEvidence(BaseModel):
    """§3.15.2 · evidence · confirmation_count ≥ 2（L2-03 二次确认）· observation_refs minItems=1。"""

    model_config = {"frozen": True}

    observation_refs: tuple[str, ...] = Field(..., min_length=1)
    tool_use_id: str | None = None
    confirmation_count: int = Field(..., ge=2)


class RequestHardHaltCommand(BaseModel):
    """§3.15.2 · request_hard_halt_command · 硬红线命中触发硬暂停。

    - require_user_authorization 硬编码 true（硬红线必须用户 IC-17 授权解除）
    - 幂等 key = red_line_id · 同 red_line_id 重复命中返回已有 halt_id 的 ack
    """

    model_config = {"frozen": True}

    halt_id: str = Field(..., pattern=r"^halt-[A-Za-z0-9_-]{3,}")
    project_id: str = Field(..., min_length=1)
    red_line_id: str = Field(..., min_length=1)
    evidence: HardHaltEvidence
    require_user_authorization: bool = Field(default=True)
    ts: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def _pid_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("E_HALT_NO_PROJECT_ID")
        return v

    @field_validator("require_user_authorization")
    @classmethod
    def _require_user_auth_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("E_HALT_USER_AUTHORIZATION_MUST_BE_TRUE")
        return v


class HardHaltState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HALTED = "HALTED"


class RequestHardHaltAck(BaseModel):
    """§3.15.3 · request_hard_halt_ack。

    halt_latency_ms 硬约束 ≤ 100ms · 超限返回 halted=true 但 L1-07 侧必告警（HRL-05）。
    """

    model_config = {"frozen": True}

    halt_id: str
    halted: bool
    halt_latency_ms: int
    state_before: HardHaltState
    state_after: HardHaltState = HardHaltState.HALTED
    audit_entry_id: str


# ==============================================================================
# 错误码枚举（供 sender 模块抛出）
# ==============================================================================


class SenderError(str, Enum):
    """IC-13 / IC-14 / IC-15 错误码集合（见 §3.13/14/15.4）。"""

    # IC-13
    SUGG_NO_PROJECT_ID = "E_SUGG_NO_PROJECT_ID"
    SUGG_LEVEL_IS_BLOCK = "E_SUGG_LEVEL_IS_BLOCK"
    SUGG_CONTENT_TOO_SHORT = "E_SUGG_CONTENT_TOO_SHORT"
    SUGG_NO_OBSERVATION = "E_SUGG_NO_OBSERVATION"
    SUGG_QUEUE_OVERFLOW = "E_SUGG_QUEUE_OVERFLOW"
    SUGG_CROSS_PROJECT = "E_SUGG_CROSS_PROJECT"
    # IC-14
    ROUTE_NO_PROJECT_ID = "E_ROUTE_NO_PROJECT_ID"
    ROUTE_WP_NOT_FOUND = "E_ROUTE_WP_NOT_FOUND"
    ROUTE_VERDICT_TARGET_MISMATCH = "E_ROUTE_VERDICT_TARGET_MISMATCH"
    ROUTE_CROSS_PROJECT = "E_ROUTE_CROSS_PROJECT"
    ROUTE_WP_ALREADY_DONE = "E_ROUTE_WP_ALREADY_DONE"
    # IC-15
    HALT_NO_PROJECT_ID = "E_HALT_NO_PROJECT_ID"
    HALT_NO_EVIDENCE = "E_HALT_NO_EVIDENCE"
    HALT_NO_CONFIRMATION = "E_HALT_NO_CONFIRMATION"
    HALT_SLO_VIOLATION = "E_HALT_SLO_VIOLATION"
    HALT_ALREADY_HALTED = "E_HALT_ALREADY_HALTED"
