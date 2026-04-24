"""L1-01 L2-03 状态机编排器 · Value Objects / DTO / Error。

7 态主状态机:
  NOT_EXIST → INITIALIZED → PLANNING → TDD_PLANNING → EXECUTING → CLOSING → CLOSED

12 合法转换(见 transition_table.ALLOWED_TRANSITIONS):
  1. NOT_EXIST → INITIALIZED
  2. INITIALIZED → PLANNING
  3. PLANNING → TDD_PLANNING
  4. TDD_PLANNING → EXECUTING
  5. EXECUTING → CLOSING
  6. CLOSING → CLOSED
  7. PLANNING → PLANNING (Re-open 自环)
  8. TDD_PLANNING → TDD_PLANNING (Re-open 自环)
  9. EXECUTING → TDD_PLANNING (L1-04 回退)
  10. EXECUTING → PLANNING (L1-04 回退)
  11. PLANNING → CLOSED (紧急终止)
  12. TDD_PLANNING → CLOSED (紧急终止)

与 L1-02 StageGateController (Dev-δ · merged) 对齐:
  - from_state/to_state enum 直接复用 app.project_lifecycle.stage_gate.schemas.ProjectState
  - 12 合法边与 stage_gate.schemas.ALLOWED_TRANSITIONS 逐字对齐 (单一来源)
  - 本 L2 是 IC-01 被调方;发 IC-01 出去只在 ic_01_producer 出现 (对称调用场景)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ------------------------------------------------------------------
# 7 态枚举 · 与 app.project_lifecycle.stage_gate.schemas.ProjectState 对齐
# ------------------------------------------------------------------
State = Literal[
    "NOT_EXIST",
    "INITIALIZED",
    "PLANNING",
    "TDD_PLANNING",
    "EXECUTING",
    "CLOSING",
    "CLOSED",
]

STATES: tuple[State, ...] = (
    "NOT_EXIST",
    "INITIALIZED",
    "PLANNING",
    "TDD_PLANNING",
    "EXECUTING",
    "CLOSING",
    "CLOSED",
)


@dataclass(frozen=True)
class Transition:
    """合法边 value object · (from, to) 标识唯一转换类型。"""

    from_state: State
    to_state: State

    def as_tuple(self) -> tuple[State, State]:
        return (self.from_state, self.to_state)


@dataclass(frozen=True)
class TransitionRequest:
    """transition() 的入参 DTO · 对齐 ic-contracts §3.1.2。

    必填: transition_id / project_id / from_state / to_state / reason /
         trigger_tick / evidence_refs / ts

    可选: gate_id (IC-01 路径非空 · IC-L2-02 路径通常 None)
    """

    transition_id: str
    project_id: str
    from_state: State
    to_state: State
    reason: str
    trigger_tick: str
    evidence_refs: tuple[str, ...]
    ts: str
    gate_id: str | None = None

    def __post_init__(self) -> None:  # pragma: no cover - 结构测试覆盖
        # 最小内在不变量(字段级语义校验留给 orchestrator 走标准错误码链路)
        if not isinstance(self.evidence_refs, tuple):
            # 允许传 list · 但 frozen · 必须在构造前 tuple()
            raise TypeError(
                "evidence_refs must be tuple (frozen dataclass); "
                "wrap with tuple(...) before constructing",
            )


@dataclass(frozen=True)
class TransitionResult:
    """transition() 的出参 DTO · 对齐 ic-contracts §3.1.3。"""

    transition_id: str
    accepted: bool
    new_state: State
    ts_applied: str
    reason: str | None = None
    error_code: str | None = None
    audit_entry_id: str | None = None


@dataclass
class StateMachineSnapshot:
    """单 session 单 project 单例 · 本 L2 内部状态。

    version: 每次成功 transition() 累加 +1;失败不变 (idempotency key 之一)。
    history: append-only list of TransitionResult。
    """

    project_id: str
    current_state: State = "NOT_EXIST"
    version: int = 0
    history: list[TransitionResult] = field(default_factory=list)


# ------------------------------------------------------------------
# 错误码 (E_TRANS_*) · 对齐 3-1 tech §3.1.4 + §3.6 总表
# ------------------------------------------------------------------
E_TRANS_INVALID_NEXT = "E_TRANS_INVALID_NEXT"
E_TRANS_STATE_MISMATCH = "E_TRANS_STATE_MISMATCH"
E_TRANS_NO_PROJECT_ID = "E_TRANS_NO_PROJECT_ID"
E_TRANS_CROSS_PROJECT = "E_TRANS_CROSS_PROJECT"
E_TRANS_REASON_TOO_SHORT = "E_TRANS_REASON_TOO_SHORT"
E_TRANS_NO_EVIDENCE = "E_TRANS_NO_EVIDENCE"
E_TRANS_CONCURRENT = "E_TRANS_CONCURRENT"
E_TRANS_IDEMPOTENT_REPLAY = "E_TRANS_IDEMPOTENT_REPLAY"
E_TRANS_INVALID_STATE_ENUM = "E_TRANS_INVALID_STATE_ENUM"
E_TRANS_TRANSITION_ID_FORMAT = "E_TRANS_TRANSITION_ID_FORMAT"

# ------------------------------------------------------------------
# MIN_REASON_LENGTH · 与 ic-contracts §3.1.2 minLength=20 对齐
# ------------------------------------------------------------------
MIN_REASON_LENGTH = 20


class StateMachineError(Exception):
    """基础异常 · 携带 error_code / project_id / context (审计追溯)。

    所有 `E_TRANS_*` 通过本异常抛出。
    部分错误 (INVALID_NEXT / CONCURRENT / STATE_MISMATCH) 不抛异常 ·
    改以 TransitionResult(accepted=False) 返回 (§3.1.4 语义)。
    """

    def __init__(
        self,
        *,
        error_code: str,
        message: str = "",
        project_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or error_code)
        self.error_code = error_code
        self.project_id = project_id
        self.context = context or {}

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"StateMachineError(error_code={self.error_code!r}, "
            f"project_id={self.project_id!r}, context={self.context!r})"
        )
