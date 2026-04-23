"""L2-01 Stage Gate 数据类型 · 对齐 tech §3 + §8。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


# 主状态机 7 态
ProjectState = Literal[
    "NOT_EXIST", "INITIALIZED", "PLANNING", "TDD_PLANNING",
    "EXECUTING", "CLOSING", "CLOSED",
]

# Gate 状态机
GateState = Literal[
    "WAITING", "OPEN", "REVIEWING", "DECIDED",
    "CLOSED", "REROUTING", "ANALYZING", "SUSPENDED",
]

Stage = Literal["S1", "S2", "S3", "S4", "S5", "S7"]  # S6 横切

Decision = Literal["pass", "reject", "need_input"]
UserDecision = Literal["approve", "reject", "request_change"]


@dataclass(frozen=True)
class EvidenceBundle:
    """stage 证据聚合 · 对齐 tech §3.1 + §6.2。"""

    project_id: str
    stage: Stage
    request_id: str
    signals: tuple[str, ...]  # e.g. ("4_pieces_ready", "9_plans_ready", "togaf_ready", "wbs_ready")
    artifacts: dict[str, Any] = field(default_factory=dict)
    trim_level: Literal["full", "minimal", "custom"] = "full"
    caller_l2: str = ""  # 谁发起 request_gate_decision（审计用）
    requested_at_ns: int = 0


@dataclass(frozen=True)
class GateDecision:
    """request_gate_decision 返回值。"""

    gate_id: str
    project_id: str
    stage: Stage
    decision: Decision
    reason: str
    missing_signals: tuple[str, ...] = ()  # need_input 时填
    root_cause: str | None = None  # reject 时 LLM 归因
    fix_advice: tuple[str, ...] = ()
    from_state: ProjectState | None = None
    to_state: ProjectState | None = None


@dataclass(frozen=True)
class TransitionResult:
    """authorize_transition 返回值。"""

    project_id: str
    from_state: ProjectState
    to_state: ProjectState
    gate_id: str
    success: bool
    emitted_ic01: bool
    reason: str = ""


@dataclass(frozen=True)
class RollbackResult:
    project_id: str
    gate_id: str
    new_re_open_count: int
    change_requests: tuple[str, ...]


@dataclass(frozen=True)
class GateStateSnapshot:
    gate_id: str
    project_id: str
    stage: Stage
    state: GateState
    re_open_count: int = 0
    created_at_ns: int = 0
    last_decision_at_ns: int = 0


# 主状态机 12 合法转换（tech §8）
ALLOWED_TRANSITIONS: tuple[tuple[ProjectState, ProjectState], ...] = (
    ("NOT_EXIST", "INITIALIZED"),
    ("INITIALIZED", "PLANNING"),
    ("PLANNING", "TDD_PLANNING"),
    ("TDD_PLANNING", "EXECUTING"),
    ("EXECUTING", "CLOSING"),
    ("CLOSING", "CLOSED"),
    # re-open 分支
    ("PLANNING", "PLANNING"),  # S2 Re-open 自环
    ("TDD_PLANNING", "TDD_PLANNING"),  # S3 Re-open
    # L1-04 级别回退（L2-01 不直接驱动 · 但视为合法历史）
    ("EXECUTING", "TDD_PLANNING"),
    ("EXECUTING", "PLANNING"),
    # 紧急终止
    ("PLANNING", "CLOSED"),  # failed_terminal 经 S7
    ("TDD_PLANNING", "CLOSED"),
)
