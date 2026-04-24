"""L1-01 L2-03 状态机编排器 · 包入口。

导出:
  - State / STATES (7 态枚举)
  - Transition (value object)
  - TransitionRequest / TransitionResult (DTO)
  - StateMachineSnapshot (单 session 聚合状态)
  - StateMachineError + 所有 E_TRANS_* 错误码常量
  - ALLOWED_TRANSITIONS / is_allowed / allowed_next (transition_table)
  - StateMachineOrchestrator (主入口 · transition())
  - IC01Producer (发 IC-01 给 L1-02 Stage Gate)
  - IdempotencyTracker (transition_id dedup)
"""
from app.main_loop.state_machine.idempotency_tracker import IdempotencyTracker
from app.main_loop.state_machine.ic_01_producer import IC01Producer
from app.main_loop.state_machine.orchestrator import StateMachineOrchestrator
from app.main_loop.state_machine.schemas import (
    E_TRANS_CONCURRENT,
    E_TRANS_CROSS_PROJECT,
    E_TRANS_IDEMPOTENT_REPLAY,
    E_TRANS_INVALID_NEXT,
    E_TRANS_INVALID_STATE_ENUM,
    E_TRANS_NO_EVIDENCE,
    E_TRANS_NO_PROJECT_ID,
    E_TRANS_REASON_TOO_SHORT,
    E_TRANS_STATE_MISMATCH,
    E_TRANS_TRANSITION_ID_FORMAT,
    MIN_REASON_LENGTH,
    STATES,
    State,
    StateMachineError,
    StateMachineSnapshot,
    Transition,
    TransitionRequest,
    TransitionResult,
)
from app.main_loop.state_machine.transition_table import (
    ALLOWED_TRANSITIONS,
    allowed_next,
    is_allowed,
)

__all__ = [
    # schemas · enums
    "State",
    "STATES",
    # schemas · DTO
    "Transition",
    "TransitionRequest",
    "TransitionResult",
    "StateMachineSnapshot",
    # schemas · errors
    "StateMachineError",
    "E_TRANS_INVALID_NEXT",
    "E_TRANS_STATE_MISMATCH",
    "E_TRANS_NO_PROJECT_ID",
    "E_TRANS_CROSS_PROJECT",
    "E_TRANS_REASON_TOO_SHORT",
    "E_TRANS_NO_EVIDENCE",
    "E_TRANS_CONCURRENT",
    "E_TRANS_IDEMPOTENT_REPLAY",
    "E_TRANS_INVALID_STATE_ENUM",
    "E_TRANS_TRANSITION_ID_FORMAT",
    "MIN_REASON_LENGTH",
    # transition_table
    "ALLOWED_TRANSITIONS",
    "is_allowed",
    "allowed_next",
    # core
    "StateMachineOrchestrator",
    "IC01Producer",
    "IdempotencyTracker",
]
