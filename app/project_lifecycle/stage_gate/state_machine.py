"""L2-01 主状态机校验 · 12 合法边 · 硬拒非法转换。"""
from __future__ import annotations

from app.project_lifecycle.stage_gate.errors import (
    E_TRANSITION_FORBIDDEN,
    StageGateError,
)
from app.project_lifecycle.stage_gate.schemas import ALLOWED_TRANSITIONS, ProjectState


def is_allowed(from_state: ProjectState, to_state: ProjectState) -> bool:
    return (from_state, to_state) in ALLOWED_TRANSITIONS


def validate_transition(
    from_state: ProjectState, to_state: ProjectState, *, project_id: str = "",
) -> None:
    if not is_allowed(from_state, to_state):
        raise StageGateError(
            error_code=E_TRANSITION_FORBIDDEN,
            message=f"illegal transition {from_state!r} → {to_state!r}",
            project_id=project_id,
            context={"from": from_state, "to": to_state},
        )
