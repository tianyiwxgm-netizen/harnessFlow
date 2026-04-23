"""L2-01 Stage Gate 控制器 · IC-01 唯一发起方 · 硬禁自动放行。

public API:
  - StageGateController(event_bus, l1_01_state_machine, config=None)
  - request_gate_decision(evidence) → GateDecision (pass/reject/need_input)
  - authorize_transition(from, to, gate_id, reason, caller='L2-01')
  - receive_user_decision(gate_id, user_decision, change_requests)
  - rollback_gate(gate_id, change_requests)
  - query_gate_state(gate_id)
"""
from app.project_lifecycle.stage_gate.controller import StageGateController
from app.project_lifecycle.stage_gate.errors import (
    StageGateError,
    StartupConfigError,
)
from app.project_lifecycle.stage_gate.ic_16_stub import (
    UIBridge,
    build_push_stage_gate_card_command,
)
from app.project_lifecycle.stage_gate.schemas import (
    ALLOWED_TRANSITIONS,
    EvidenceBundle,
    GateDecision,
    GateState,
    GateStateSnapshot,
    ProjectState,
    RollbackResult,
    Stage,
    TransitionResult,
)
from app.project_lifecycle.stage_gate.state_machine import (
    is_allowed,
    validate_transition,
)

__all__ = [
    "StageGateController",
    "StageGateError",
    "StartupConfigError",
    "EvidenceBundle",
    "GateDecision",
    "GateStateSnapshot",
    "RollbackResult",
    "TransitionResult",
    "ProjectState",
    "GateState",
    "Stage",
    "ALLOWED_TRANSITIONS",
    "is_allowed",
    "validate_transition",
    "UIBridge",
    "build_push_stage_gate_card_command",
]
