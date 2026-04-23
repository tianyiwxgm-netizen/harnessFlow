"""L2-02 Kickoff 数据类型 · 对齐 L2-02 tech §3 + §7。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TrimLevel = Literal["full", "minimal", "custom"]
KickoffState = Literal[
    "DRAFT", "CLARIFYING", "CHARTER_GEN", "STAKEHOLDERS_GEN",
    "GOAL_ANCHOR_LOCKING", "DONE", "INITIALIZED",
]


@dataclass(frozen=True)
class KickoffRequest:
    """IC-L2-01 入参（L2-01 → L2-02）· 对齐 tech §3.2.1。"""

    trigger_id: str
    stage: str
    user_initial_goal: str
    caller_l2: str
    trim_level: TrimLevel = "full"
    preexisting_charter_path: str | None = None
    trace_ctx: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CharterFields:
    """Charter 8 必填字段 · 对齐 tech §3.3 + I-L202-03。"""

    title: str
    purpose: str
    scope: dict[str, list[str]]  # {in_scope: [...], out_of_scope: [...]}
    success_criteria: list[str]
    constraints: list[str] = field(default_factory=list)
    risks_initial: list[str] = field(default_factory=list)
    stakeholders_initial: list[str] = field(default_factory=list)
    authority: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StakeholdersEntry:
    """干系人单条目 · 对齐 tech §3.4。"""

    role: str
    who: str
    influence: Literal["high", "medium", "low"]
    raci: Literal["R", "A", "C", "I"] | None = None


@dataclass(frozen=True)
class KickoffSuccess:
    """kickoff_create_project 成功返回 · 对齐 tech §3.2.2。"""

    project_id: str
    charter_path: str
    stakeholders_path: str
    manifest_path: str
    goal_anchor_hash: str
    clarification_rounds: int
    clarification_incomplete: bool = False
    events_published: tuple[str, ...] = ()
    trim_level_applied: TrimLevel = "full"


@dataclass(frozen=True)
class KickoffErr:
    """kickoff_create_project 失败返回 · 对齐 tech §3.2.2。"""

    err_code: str
    reason: str
    suggested_action: str | None = None
    partial_project_id: str | None = None


@dataclass(frozen=True)
class KickoffResponse:
    """IC-L2-01 出参 · 对齐 tech §3.2.2。"""

    trigger_id: str
    status: Literal["ok", "err", "degraded"]
    result: KickoffSuccess | KickoffErr
    latency_ms: int = 0


@dataclass(frozen=True)
class ActivateRequest:
    """activate_project_id 入参 · 对齐 tech §3.5。"""

    project_id: str
    goal_anchor_hash: str
    user_confirmed: bool
    charter_path: str
    stakeholders_path: str
    caller_l2: str = "L2-01"  # PM-14 硬约束 · 非 L2-01 拒绝


@dataclass(frozen=True)
class ActivateResponse:
    """activate_project_id 出参 · 对齐 tech §3.5。"""

    project_id: str
    state: Literal["INITIALIZED"]
    activated_at: str
    meta_path: str


@dataclass(frozen=True)
class RecoveryResult:
    """recover_draft 返回值 · 对齐 tech §6.5。"""

    action: Literal["no_op", "resumed", "rolled_back"]
    project_id: str
    reason: str | None = None


@dataclass(frozen=True)
class WriteResult:
    """atomic_write_chart 返回值。"""

    path: str
    bytes_written: int
    sha256: str
